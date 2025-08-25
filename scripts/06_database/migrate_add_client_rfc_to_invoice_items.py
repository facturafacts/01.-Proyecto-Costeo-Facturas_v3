#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add client_rfc and approved_sku_id to invoice_items with helpful indexes.
Idempotent and supports PostgreSQL and SQLite.
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Ensure project root for config import
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_invoice_items_cols")


def main() -> int:
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        dialect = engine.url.get_dialect().name
        with engine.begin() as conn:
            logger.info(f"Detected DB dialect: {dialect}")

            # Verify table exists
            if dialect == 'postgresql':
                table_exists = conn.execute(text(
                    """
                    SELECT EXISTS (
                      SELECT 1 FROM information_schema.tables
                      WHERE table_schema = 'public' AND table_name = 'invoice_items'
                    )
                    """
                )).scalar()
            elif dialect == 'sqlite':
                res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice_items'"))
                table_exists = res.fetchone() is not None
            else:
                raise RuntimeError(f"Unsupported dialect: {dialect}")

            if not table_exists:
                logger.error("Table 'invoice_items' does not exist. Run setup first.")
                return 2

            if dialect == 'postgresql':
                logger.info("Adding columns client_rfc and approved_sku_id (nullable)...")
                conn.execute(text(
                    """
                    ALTER TABLE invoice_items
                    ADD COLUMN IF NOT EXISTS client_rfc VARCHAR(13) NULL;
                    """
                ))
                conn.execute(text(
                    """
                    ALTER TABLE invoice_items
                    ADD COLUMN IF NOT EXISTS approved_sku_id INTEGER NULL REFERENCES approved_skus(id);
                    """
                ))

                logger.info("Creating indexes (client_rfc, sku_key) and approved_sku_id...")
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_item_client_sku ON invoice_items (client_rfc, sku_key)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_item_approved_sku_id ON invoice_items (approved_sku_id)"
                ))

            elif dialect == 'sqlite':
                logger.info("SQLite migration: adding columns if missing...")
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info('invoice_items')")).fetchall()]
                if 'client_rfc' not in cols:
                    conn.execute(text("ALTER TABLE invoice_items ADD COLUMN client_rfc TEXT"))
                if 'approved_sku_id' not in cols:
                    conn.execute(text("ALTER TABLE invoice_items ADD COLUMN approved_sku_id INTEGER"))

                logger.info("Creating indexes...")
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_item_client_sku ON invoice_items (client_rfc, sku_key)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_item_approved_sku_id ON invoice_items (approved_sku_id)"
                ))

        logger.info("Migration completed successfully.")
        return 0
    except SQLAlchemyError as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


