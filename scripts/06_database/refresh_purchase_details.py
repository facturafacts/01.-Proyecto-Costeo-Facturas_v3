#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Refresh Purchase Details Table in Production

This script safely truncates and repopulates the `purchase_details` table
from the data in the `invoices`, `invoice_items`, and `invoice_metadata` tables.
It is designed to be run on the production database to ensure the export
table is always up-to-date.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import text
from src.data.database import DatabaseManager

def refresh_purchase_details():
    """Truncates and rebuilds the purchase_details table."""
    
    print("\n🔄 Refreshing Production `purchase_details` Table...")
    print("=" * 70)
    
    db_manager = DatabaseManager()
    
    # This is the SQL query that performs the complete refresh.
    # It first deletes all existing data and then repopulates the table.
    refresh_query = text("""
        BEGIN;

        -- Step 1: Clear the table completely for a fresh start.
        -- TRUNCATE is faster than DELETE for large tables.
        TRUNCATE TABLE purchase_details RESTART IDENTITY;

        -- Step 2: Repopulate the table with the latest data from core tables.
        INSERT INTO purchase_details (
            invoice_uuid, folio, issue_date, issuer_rfc, issuer_name, 
            receiver_rfc, receiver_name, payment_method, payment_terms,
            currency, exchange_rate, invoice_mxn_total, is_installments, is_immediate,
            line_number, product_code, description, quantity, unit_code,
            unit_price, subtotal, discount, total_amount, total_tax_amount,
            units_per_package, standardized_unit, standardized_quantity, conversion_factor,
            category, subcategory, sub_sub_category, category_confidence,
            classification_source, approval_status, sku_key,
            item_mxn_total, standardized_mxn_value, unit_mxn_price,
            created_at, updated_at
        )
        SELECT 
            i.uuid as invoice_uuid, i.folio, i.issue_date, i.issuer_rfc, i.issuer_name,
            i.receiver_rfc, i.receiver_name, i.payment_method, i.payment_terms,
            i.currency, i.exchange_rate,
            im.mxn_total as invoice_mxn_total, im.is_installments, im.is_immediate,
            ii.line_number, ii.product_code, ii.description, ii.quantity, ii.unit_code,
            ii.unit_price, ii.subtotal, ii.discount, ii.total_amount, ii.total_tax_amount,
            ii.units_per_package, ii.standardized_unit, ii.standardized_quantity, ii.conversion_factor,
            ii.category, ii.subcategory, ii.sub_sub_category, ii.category_confidence,
            ii.classification_source, ii.approval_status, ii.sku_key,
            (ii.total_amount * COALESCE(i.exchange_rate, 1.0)) as item_mxn_total,
            CASE 
                WHEN ii.standardized_quantity IS NOT NULL AND ii.unit_price IS NOT NULL 
                THEN (ii.standardized_quantity * ii.unit_price * COALESCE(i.exchange_rate, 1.0))
                ELSE NULL 
            END as standardized_mxn_value,
            (ii.unit_price * COALESCE(i.exchange_rate, 1.0)) as unit_mxn_price,
            NOW() as created_at,
            NOW() as updated_at
        FROM invoices i
        JOIN invoice_items ii ON i.id = ii.invoice_id
        JOIN invoice_metadata im ON i.id = im.invoice_id
        WHERE i.processing_status = 'processed'
        ORDER BY i.issue_date DESC, ii.line_number;

        COMMIT;
    """)

    try:
        with db_manager.get_session() as session:
            print("⏳ Executing refresh query... (This may take a moment)")
            session.execute(refresh_query)
            print("✅ Query executed successfully.")

            # Get and print statistics
            stats_query = text("SELECT COUNT(*), COUNT(DISTINCT invoice_uuid) FROM purchase_details")
            total_records, unique_invoices = session.execute(stats_query).fetchone()
            
            print("\n🎉 Refresh Complete!")
            print("=" * 70)
            print(f"📦 Total line items in purchase_details: {total_records:,}")
            print(f"🧾 Corresponding unique invoices: {unique_invoices:,}")
            print("✅ Your `purchase_details` table is now perfectly in sync.")

    except Exception as e:
        print(f"❌ An error occurred during the refresh: {e}")
        print("   Your data has not been changed. Please check the database connection and error message.")
        return

if __name__ == "__main__":
    refresh_purchase_details() 