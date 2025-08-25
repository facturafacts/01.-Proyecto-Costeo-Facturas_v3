#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill invoice_items from approved_skus per client (preview-friendly).

Features:
- --dry-run: prints counts and a sample of per-item before/after without writing
- Prefills invoice_items.client_rfc from invoices.receiver_rfc if missing
- Links approved_sku_id via (client_rfc, sku_key)
- Updates approval_status and classification fields from approved_skus

Usage:
  python scripts/06_database/backfill_invoice_items_from_approved_skus.py --dry-run
  python scripts/06_database/backfill_invoice_items_from_approved_skus.py
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Ensure project root for config import
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_invoice_items")


def main() -> int:
    dry_run: bool = '--dry-run' in sys.argv
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        dialect = engine.url.get_dialect().name
        with engine.begin() as conn:
            logger.info(f"Dialect: {dialect}; Dry-run: {dry_run}")

            # 1) Prefill invoice_items.client_rfc from invoices when NULL
            logger.info("Prefilling invoice_items.client_rfc from invoices.receiver_rfc if missing...")
            if dialect == 'postgresql':
                missing = conn.execute(text(
                    "SELECT COUNT(*) FROM invoice_items WHERE client_rfc IS NULL"
                )).scalar() or 0
                logger.info(f"invoice_items.client_rfc NULL rows: {missing}")
                if missing > 0 and not dry_run:
                    conn.execute(text(
                        """
                        UPDATE invoice_items ii
                        SET client_rfc = inv.receiver_rfc
                        FROM invoices inv
                        WHERE ii.client_rfc IS NULL
                          AND ii.invoice_id = inv.id
                        """
                    ))
            elif dialect == 'sqlite':
                missing = conn.execute(text(
                    "SELECT COUNT(*) FROM invoice_items WHERE client_rfc IS NULL"
                )).scalar() or 0
                logger.info(f"invoice_items.client_rfc NULL rows: {missing}")
                if missing > 0 and not dry_run:
                    conn.execute(text(
                        """
                        UPDATE invoice_items
                        SET client_rfc = (
                          SELECT receiver_rfc FROM invoices inv
                          WHERE inv.id = invoice_items.invoice_id
                        )
                        WHERE client_rfc IS NULL
                        """
                    ))
            else:
                raise RuntimeError(f"Unsupported dialect: {dialect}")

            # 2) Preview counts and sample of what will be updated
            logger.info("Computing item link and update counts...")
            to_link = conn.execute(text(
                """
                SELECT COUNT(*)
                FROM invoice_items ii
                JOIN approved_skus s
                  ON s.sku_key = ii.sku_key
                 AND s.client_rfc = ii.client_rfc
                WHERE ii.approved_sku_id IS NULL
                """
            )).scalar() or 0
            to_update = conn.execute(text(
                """
                SELECT COUNT(*)
                FROM invoice_items ii
                JOIN approved_skus s
                  ON s.sku_key = ii.sku_key
                 AND s.client_rfc = ii.client_rfc
                WHERE (
                  ii.approval_status <> 'approved'
                  OR ii.category IS NULL
                  OR ii.subcategory IS NULL
                  OR ii.sub_sub_category IS NULL
                  OR ii.standardized_unit IS NULL
                  OR ii.units_per_package IS NULL
                )
                """
            )).scalar() or 0

            logger.info(f"Items to link approved_sku_id: {to_link}")
            logger.info(f"Items to update classification fields: {to_update}")

            # Preview sample rows for transparency
            preview_limit: int = 50
            preview_rows = conn.execute(text(
                """
                SELECT ii.id, ii.invoice_id, ii.client_rfc, ii.sku_key,
                       ii.approval_status AS before_status,
                       ii.category AS before_cat, ii.subcategory AS before_sub,
                       ii.sub_sub_category AS before_subsub,
                       ii.standardized_unit AS before_unit,
                       ii.units_per_package AS before_units_per_pack,
                       s.id AS approved_sku_id,
                       s.category AS new_cat, s.subcategory AS new_sub,
                       s.sub_sub_category AS new_subsub,
                       s.standardized_unit AS new_unit,
                       s.units_per_package AS new_units_per_pack
                FROM invoice_items ii
                JOIN approved_skus s
                  ON s.sku_key = ii.sku_key
                 AND s.client_rfc = ii.client_rfc
                WHERE (
                  ii.approved_sku_id IS NULL
                  OR ii.approval_status <> 'approved'
                  OR ii.category IS NULL
                  OR ii.subcategory IS NULL
                  OR ii.sub_sub_category IS NULL
                  OR ii.standardized_unit IS NULL
                  OR ii.units_per_package IS NULL
                )
                ORDER BY ii.id
                LIMIT :limit
                """
            ), {"limit": preview_limit}).fetchall()

            logger.info(f"Previewing up to {preview_limit} items that would be updated:")
            for r in preview_rows:
                logger.info(
                    f"ii.id={r.id} inv={r.invoice_id} rfc={r.client_rfc} sku={r.sku_key} "
                    f"status {r.before_status} -> approved | "
                    f"cat {r.before_cat} -> {r.new_cat} | sub {r.before_sub} -> {r.new_sub} | "
                    f"subsub {r.before_subsub} -> {r.new_subsub} | unit {r.before_unit} -> {r.new_unit} | "
                    f"units/pack {r.before_units_per_pack} -> {r.new_units_per_pack} | approved_sku_id {r.approved_sku_id}"
                )

            if dry_run:
                logger.info("Dry-run complete. No changes applied.")
                return 0

            # 3) Apply linking of approved_sku_id (PostgreSQL) or SQLite equivalent
            logger.info("Linking approved_sku_id on invoice_items...")
            if dialect == 'postgresql':
                conn.execute(text(
                    """
                    UPDATE invoice_items ii
                    SET approved_sku_id = s.id
                    FROM approved_skus s
                    WHERE ii.approved_sku_id IS NULL
                      AND ii.sku_key = s.sku_key
                      AND ii.client_rfc = s.client_rfc
                    """
                ))
            else:  # sqlite
                conn.execute(text(
                    """
                    UPDATE invoice_items
                    SET approved_sku_id = (
                      SELECT s.id FROM approved_skus s
                      WHERE s.sku_key = invoice_items.sku_key
                        AND s.client_rfc = invoice_items.client_rfc
                    )
                    WHERE approved_sku_id IS NULL
                    """
                ))

            # 4) Apply classification updates from approved_skus
            logger.info("Updating invoice_items classification fields from approved_skus...")
            if dialect == 'postgresql':
                conn.execute(text(
                    """
                    UPDATE invoice_items ii
                    SET approval_status = 'approved',
                        category = s.category,
                        subcategory = s.subcategory,
                        sub_sub_category = s.sub_sub_category,
                        standardized_unit = s.standardized_unit,
                        units_per_package = s.units_per_package
                    FROM approved_skus s
                    WHERE ii.sku_key = s.sku_key
                      AND ii.client_rfc = s.client_rfc
                      AND (
                        ii.approval_status <> 'approved'
                        OR ii.category IS NULL
                        OR ii.subcategory IS NULL
                        OR ii.sub_sub_category IS NULL
                        OR ii.standardized_unit IS NULL
                        OR ii.units_per_package IS NULL
                      )
                    """
                ))
            else:  # sqlite
                conn.execute(text(
                    """
                    UPDATE invoice_items
                    SET approval_status = 'approved',
                        category = (
                          SELECT s.category FROM approved_skus s
                          WHERE s.sku_key = invoice_items.sku_key AND s.client_rfc = invoice_items.client_rfc
                        ),
                        subcategory = (
                          SELECT s.subcategory FROM approved_skus s
                          WHERE s.sku_key = invoice_items.sku_key AND s.client_rfc = invoice_items.client_rfc
                        ),
                        sub_sub_category = (
                          SELECT s.sub_sub_category FROM approved_skus s
                          WHERE s.sku_key = invoice_items.sku_key AND s.client_rfc = invoice_items.client_rfc
                        ),
                        standardized_unit = (
                          SELECT s.standardized_unit FROM approved_skus s
                          WHERE s.sku_key = invoice_items.sku_key AND s.client_rfc = invoice_items.client_rfc
                        ),
                        units_per_package = (
                          SELECT s.units_per_package FROM approved_skus s
                          WHERE s.sku_key = invoice_items.sku_key AND s.client_rfc = invoice_items.client_rfc
                        )
                    WHERE (
                      approval_status <> 'approved'
                      OR category IS NULL
                      OR subcategory IS NULL
                      OR sub_sub_category IS NULL
                      OR standardized_unit IS NULL
                      OR units_per_package IS NULL
                    )
                    """
                ))

            logger.info("Backfill applied successfully.")
            return 0

    except SQLAlchemyError as e:
        logger.error(f"Backfill failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


