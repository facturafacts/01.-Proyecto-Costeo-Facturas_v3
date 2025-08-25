#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time migration: add client_rfc to approved_skus and enforce per-client uniqueness.

Safe order:
1) Add nullable column client_rfc
2) Create composite index and unique constraint
3) Optionally backfill values later
4) (Later) Alter to NOT NULL after backfill
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Ensure project root is on sys.path so 'config' package resolves when running this file directly
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_client_rfc")


def main() -> int:
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        dialect = engine.url.get_dialect().name
        with engine.begin() as conn:
            logger.info(f"Detected DB dialect: {dialect}")

            # Verify approved_skus table exists
            if dialect == 'postgresql':
                tbl_exists = conn.execute(text(
                    """
                    SELECT EXISTS (
                      SELECT 1 FROM information_schema.tables 
                      WHERE table_schema = 'public' AND table_name = 'approved_skus'
                    )
                    """
                )).scalar()
            elif dialect == 'sqlite':
                res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='approved_skus'"))
                tbl_exists = res.fetchone() is not None
            else:
                raise RuntimeError(f"Unsupported dialect for this migration: {dialect}")

            if not tbl_exists:
                logger.error("Table 'approved_skus' does not exist. Run initial setup (scripts/01_setup/setup_database.py) first.")
                return 2

            if dialect == 'postgresql':
                logger.info("Adding column client_rfc (nullable) to approved_skus...")
                conn.execute(text(
                    """
                    ALTER TABLE approved_skus
                    ADD COLUMN IF NOT EXISTS client_rfc VARCHAR(13) NULL;
                    """
                ))

                logger.info("Dropping old unique constraint on sku_key if exists...")
                try:
                    conn.execute(text(
                        """
                        DO $$ BEGIN
                          IF EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname = 'approved_skus_sku_key_key'
                          ) THEN
                            ALTER TABLE approved_skus DROP CONSTRAINT approved_skus_sku_key_key;
                          END IF;
                        END $$;
                        """
                    ))
                except Exception:
                    pass

                logger.info("Creating composite unique constraint uq_client_sku_key...")
                conn.execute(text(
                    """
                    DO $$ BEGIN
                      IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_client_sku_key'
                      ) THEN
                        ALTER TABLE approved_skus
                        ADD CONSTRAINT uq_client_sku_key UNIQUE (client_rfc, sku_key);
                      END IF;
                    END $$;
                    """
                ))

                logger.info("Creating index idx_sku_client_key...")
                conn.execute(text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sku_client_key
                    ON approved_skus (client_rfc, sku_key);
                    """
                ))

            elif dialect == 'sqlite':
                logger.info("SQLite detected - applying compatible migration...")

                # Add column if not exists (SQLite supports ADD COLUMN but not IF NOT EXISTS)
                # Check pragma for existing columns
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info('approved_skus')")).fetchall()]
                if 'client_rfc' not in cols:
                    logger.info("Adding client_rfc column to approved_skus (SQLite)...")
                    conn.execute(text("ALTER TABLE approved_skus ADD COLUMN client_rfc TEXT"))

                # Create a unique index to emulate unique constraint per client
                logger.info("Creating unique index uq_client_sku_key (SQLite)...")
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_client_sku_key ON approved_skus (client_rfc, sku_key)"
                ))

                logger.info("Creating index idx_sku_client_key (SQLite)...")
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_sku_client_key ON approved_skus (client_rfc, sku_key)"
                ))

            else:
                raise RuntimeError(f"Unsupported dialect for this migration: {dialect}")

        logger.info("Migration completed successfully.")
        return 0
    except SQLAlchemyError as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


