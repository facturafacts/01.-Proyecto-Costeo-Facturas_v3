#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill client_rfc into approved_skus and link invoice_items.approved_sku_id.

Strategy:
- Build usage map from invoice_items: sku_key -> set(client_rfcs)
- For each approved_skus row without client_rfc:
  - If usage map has 1 RFC: set that RFC
  - If multiple RFCs: duplicate row per RFC and delete original
- Then set invoice_items.approved_sku_id by joining on (client_rfc, sku_key)

Safe & idempotent with --dry-run option.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Set
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Ensure project root for config import
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_client_rfc")


def main() -> int:
    dry_run = '--dry-run' in sys.argv
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        dialect = engine.url.get_dialect().name
        with engine.begin() as conn:
            logger.info(f"Dialect: {dialect}; Dry-run: {dry_run}")

            # 0) Pre-fill invoice_items.client_rfc from invoices.receiver_rfc
            logger.info("Prefilling invoice_items.client_rfc from invoices.receiver_rfc if missing...")
            if dialect == 'postgresql':
                # Count missing first
                missing = conn.execute(text(
                    """
                    SELECT COUNT(*)
                    FROM invoice_items ii
                    WHERE ii.client_rfc IS NULL
                    """
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
                          SELECT receiver_rfc
                          FROM invoices inv
                          WHERE inv.id = invoice_items.invoice_id
                        )
                        WHERE client_rfc IS NULL
                        """
                    ))

            # 1) Build usage map from invoice_items
            logger.info("Building usage map from invoice_items and purchase_details...")
            usage_rows = []
            usage_rows += conn.execute(text(
                "SELECT sku_key, client_rfc FROM invoice_items WHERE sku_key IS NOT NULL AND client_rfc IS NOT NULL"
            )).fetchall()
            # Fallback/additional source: purchase_details
            # Note: column is receiver_rfc in purchase_details
            usage_rows += conn.execute(text(
                "SELECT sku_key, receiver_rfc AS client_rfc FROM purchase_details WHERE sku_key IS NOT NULL AND receiver_rfc IS NOT NULL"
            )).fetchall()
            sku_to_rfcs: Dict[str, Set[str]] = {}
            for sku_key, client_rfc in usage_rows:
                if not sku_key or not client_rfc:
                    continue
                sku_to_rfcs.setdefault(sku_key, set()).add(client_rfc)
            logger.info(f"Found {len(sku_to_rfcs)} sku_keys with client usage")

            # 2) Backfill approved_skus.client_rfc
            logger.info("Fetching approved_skus without client_rfc...")
            aprows = conn.execute(text(
                "SELECT id, sku_key FROM approved_skus WHERE client_rfc IS NULL OR client_rfc = ''"
            )).fetchall()
            logger.info(f"Rows needing client_rfc: {len(aprows)}")

            created = 0
            updated = 0
            for row in aprows:
                sku_id, sku_key = row
                rfcs = list(sku_to_rfcs.get(sku_key, []))
                if not rfcs:
                    logger.info(f"No usage found for sku_key={sku_key}; skipping")
                    continue
                if len(rfcs) == 1:
                    rfc = rfcs[0]
                    logger.info(f"Updating approved_skus id={sku_id} -> client_rfc={rfc}")
                    if not dry_run:
                        conn.execute(text("UPDATE approved_skus SET client_rfc=:rfc WHERE id=:id"), {"rfc": rfc, "id": sku_id})
                    updated += 1
                else:
                    logger.info(f"Duplicating approved_skus id={sku_id} for rfcs={rfcs}")
                    # Fetch template row
                    tpl = conn.execute(text("SELECT sku_key, product_code, internal_code, normalized_description, category, subcategory, sub_sub_category, standardized_unit, correct_unit_code, units_per_package, package_type, conversion_notes, typical_quantity_range, approved_by, approval_date, confidence_score, usage_count, last_used, review_status, review_notes, created_at, updated_at FROM approved_skus WHERE id=:id"), {"id": sku_id}).fetchone()
                    if not dry_run:
                        # Delete original ambiguous row
                        conn.execute(text("DELETE FROM approved_skus WHERE id=:id"), {"id": sku_id})
                    for rfc in rfcs:
                        logger.info(f"Creating per-client approved_skus for {rfc}, sku_key={sku_key}")
                        if not dry_run:
                            conn.execute(text(
                                """
                                INSERT INTO approved_skus (
                                    client_rfc, sku_key, product_code, internal_code, normalized_description,
                                    category, subcategory, sub_sub_category, standardized_unit, correct_unit_code,
                                    units_per_package, package_type, conversion_notes, typical_quantity_range,
                                    approved_by, approval_date, confidence_score, usage_count, last_used,
                                    review_status, review_notes, created_at, updated_at
                                ) VALUES (
                                    :client_rfc, :sku_key, :product_code, :internal_code, :normalized_description,
                                    :category, :subcategory, :sub_sub_category, :standardized_unit, :correct_unit_code,
                                    :units_per_package, :package_type, :conversion_notes, :typical_quantity_range,
                                    :approved_by, :approval_date, :confidence_score, :usage_count, :last_used,
                                    :review_status, :review_notes, :created_at, :updated_at
                                )
                                """
                            ), {
                                "client_rfc": rfc,
                                "sku_key": sku_key,
                                "product_code": tpl.product_code,
                                "internal_code": tpl.internal_code,
                                "normalized_description": tpl.normalized_description,
                                "category": tpl.category,
                                "subcategory": tpl.subcategory,
                                "sub_sub_category": tpl.sub_sub_category,
                                "standardized_unit": tpl.standardized_unit,
                                "correct_unit_code": tpl.correct_unit_code,
                                "units_per_package": tpl.units_per_package,
                                "package_type": tpl.package_type,
                                "conversion_notes": tpl.conversion_notes,
                                "typical_quantity_range": tpl.typical_quantity_range,
                                "approved_by": tpl.approved_by,
                                "approval_date": tpl.approval_date,
                                "confidence_score": tpl.confidence_score,
                                "usage_count": tpl.usage_count,
                                "last_used": tpl.last_used,
                                "review_status": tpl.review_status,
                                "review_notes": tpl.review_notes,
                                "created_at": tpl.created_at,
                                "updated_at": tpl.updated_at,
                            })
                        created += 1

            logger.info(f"Backfill summary: updated={updated}, created={created}")

            # 3) Link invoice_items to approved_skus via approved_sku_id
            logger.info("Linking invoice_items.approved_sku_id...")
            if not dry_run:
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

        logger.info("Backfill completed.")
        return 0
    except SQLAlchemyError as e:
        logger.error(f"Backfill failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


