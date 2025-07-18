#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone script to create purchase_details table in LOCAL SQLite database

This script forces SQLite usage regardless of .env settings to fix the local database structure.
Run this BEFORE migrating to PostgreSQL.
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def create_purchase_details_table_local() -> bool:
    """Create and populate the purchase_details table in LOCAL SQLite database."""
    try:
        # Force local SQLite path
        project_root = Path(__file__).parent
        db_path = project_root / "data" / "database" / "cfdi_system_v4.db"
        
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return False
        
        print("\n🛒 Creating Purchase Details Table for Google Sheets Export (LOCAL SQLite)")
        print("=" * 70)
        print(f"📁 Database: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Drop existing table to start fresh
        print("🗑️  Dropping existing purchase_details table...")
        cursor.execute("DROP TABLE IF EXISTS purchase_details")
        
        # 2. Create the NEW purchase_details table with flattened structure
        print("📋 Creating NEW purchase_details table...")
        cursor.execute("""
            CREATE TABLE purchase_details (
                -- Primary Key
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Invoice Information
                invoice_uuid VARCHAR(36) NOT NULL,
                folio VARCHAR(40),
                issue_date DATE NOT NULL,
                issuer_rfc VARCHAR(13) NOT NULL,
                issuer_name VARCHAR(254),
                receiver_rfc VARCHAR(13) NOT NULL,
                receiver_name VARCHAR(254),
                payment_method VARCHAR(2),
                payment_terms VARCHAR(10),
                currency VARCHAR(3) NOT NULL DEFAULT 'MXN',
                exchange_rate DECIMAL(15,6) NOT NULL DEFAULT 1.0,
                
                -- Metadata Business Logic
                invoice_mxn_total DECIMAL(15,2) NOT NULL,
                is_installments BOOLEAN NOT NULL DEFAULT 0,
                is_immediate BOOLEAN NOT NULL DEFAULT 1,
                
                -- Item Details
                line_number INTEGER NOT NULL,
                product_code VARCHAR(50),
                description TEXT NOT NULL,
                quantity DECIMAL(15,6) NOT NULL,
                unit_code VARCHAR(10),
                unit_price DECIMAL(15,6) NOT NULL,
                subtotal DECIMAL(15,2) NOT NULL,
                discount DECIMAL(15,2) NOT NULL DEFAULT 0,
                total_amount DECIMAL(15,2) NOT NULL,
                total_tax_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                
                -- Enhanced Item Info
                units_per_package DECIMAL(15,6),
                standardized_unit VARCHAR(20),
                standardized_quantity DECIMAL(15,6),
                conversion_factor DECIMAL(15,6),
                
                -- AI Classification
                category VARCHAR(50),
                subcategory VARCHAR(100),
                sub_sub_category VARCHAR(150),
                category_confidence DECIMAL(5,2),
                classification_source VARCHAR(20),
                approval_status VARCHAR(20) DEFAULT 'pending',
                sku_key VARCHAR(255),
                
                -- Calculated Fields (MXN conversions)
                item_mxn_total DECIMAL(15,2) NOT NULL,
                standardized_mxn_value DECIMAL(15,2),
                unit_mxn_price DECIMAL(15,6) NOT NULL,
                
                -- Processing metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 3. Create indexes for performance
        print("🚀 Creating indexes...")
        indexes = [
            "CREATE INDEX idx_purchase_details_issue_date ON purchase_details(issue_date)",
            "CREATE INDEX idx_purchase_details_issuer ON purchase_details(issuer_rfc)",
            "CREATE INDEX idx_purchase_details_category ON purchase_details(category)",
            "CREATE INDEX idx_purchase_details_product ON purchase_details(product_code)",
            "CREATE INDEX idx_purchase_details_approval ON purchase_details(approval_status)",
            "CREATE INDEX idx_purchase_details_sku_key ON purchase_details(sku_key)",
            "CREATE INDEX idx_purchase_details_uuid ON purchase_details(invoice_uuid)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # 4. Check if we have existing data to populate
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        if invoice_count > 0:
            print(f"📊 Found {invoice_count} existing invoices. Populating purchase_details table...")
            
            # Populate the table with existing data using the corrected query
            cursor.execute("""
                INSERT INTO purchase_details (
                    invoice_uuid, folio, issue_date, issuer_rfc, issuer_name, 
                    receiver_rfc, receiver_name, payment_method, payment_terms,
                    currency, exchange_rate, invoice_mxn_total, is_installments, is_immediate,
                    line_number, product_code, description, quantity, unit_code,
                    unit_price, subtotal, discount, total_amount, total_tax_amount,
                    units_per_package, standardized_unit, standardized_quantity, conversion_factor,
                    category, subcategory, sub_sub_category, category_confidence,
                    classification_source, approval_status, sku_key,
                    item_mxn_total, standardized_mxn_value, unit_mxn_price
                )
                SELECT 
                    -- Invoice Info
                    i.uuid as invoice_uuid,
                    i.folio,
                    DATE(i.issue_date) as issue_date,
                    i.issuer_rfc,
                    i.issuer_name,
                    i.receiver_rfc,
                    i.receiver_name,
                    i.payment_method,
                    i.payment_terms,
                    i.currency,
                    COALESCE(i.exchange_rate, 1.0) as exchange_rate,
                    
                    -- Metadata Business Logic
                    COALESCE(im.mxn_total, i.total_amount * COALESCE(i.exchange_rate, 1.0)) as invoice_mxn_total,
                    COALESCE(im.is_installments, 0) as is_installments,
                    COALESCE(im.is_immediate, 1) as is_immediate,
                    
                    -- Item Details
                    ii.line_number,
                    ii.product_code,
                    ii.description,
                    ii.quantity,
                    ii.unit_code,
                    ii.unit_price,
                    ii.subtotal,
                    COALESCE(ii.discount, 0) as discount,
                    ii.total_amount,
                    COALESCE(ii.total_tax_amount, 0) as total_tax_amount,
                    
                    -- Enhanced Item Info
                    ii.units_per_package,
                    ii.standardized_unit,
                    ii.standardized_quantity,
                    ii.conversion_factor,
                    
                    -- AI Classification
                    ii.category,
                    ii.subcategory,
                    ii.sub_sub_category,
                    ii.category_confidence,
                    COALESCE(ii.classification_source, 'pending') as classification_source,
                    COALESCE(ii.approval_status, 'pending') as approval_status,
                    ii.sku_key,
                    
                    -- Calculated Fields
                    (ii.total_amount * COALESCE(i.exchange_rate, 1.0)) as item_mxn_total,
                    CASE 
                        WHEN ii.standardized_quantity IS NOT NULL AND ii.unit_price IS NOT NULL 
                        THEN (ii.standardized_quantity * ii.unit_price * COALESCE(i.exchange_rate, 1.0))
                        ELSE NULL 
                    END as standardized_mxn_value,
                    (ii.unit_price * COALESCE(i.exchange_rate, 1.0)) as unit_mxn_price
                    
                FROM invoices i
                JOIN invoice_items ii ON i.id = ii.invoice_id
                LEFT JOIN invoice_metadata im ON i.id = im.invoice_id
                ORDER BY i.issue_date DESC, ii.line_number
            """)
        else:
            print("📊 No existing invoices found. Purchase_details table created and ready.")
        
        # 5. Get statistics
        cursor.execute("SELECT COUNT(*) FROM purchase_details")
        total_records = cursor.fetchone()[0]
        
        if total_records > 0:
            cursor.execute("SELECT COUNT(DISTINCT invoice_uuid) FROM purchase_details")
            unique_invoices = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM purchase_details WHERE approval_status = 'approved'")
            approved_items = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(issue_date), MAX(issue_date) FROM purchase_details")
            date_range = cursor.fetchone()
            
            cursor.execute("SELECT SUM(item_mxn_total) FROM purchase_details")
            total_mxn_value = cursor.fetchone()[0] or 0
            
            print("\n✅ Purchase Details Table Created Successfully!")
            print("=" * 70)
            print(f"📦 Total line items: {total_records:,}")
            print(f"🧾 Unique invoices: {unique_invoices:,}")
            print(f"✅ Approved classifications: {approved_items:,}")
            print(f"📅 Date range: {date_range[0]} to {date_range[1]}")
            print(f"💰 Total MXN value: ${total_mxn_value:,.2f}")
            print(f"📊 Success rate: {(approved_items/total_records*100):.1f}%")
            
            # Show sample data
            print("\n📋 Sample Records:")
            cursor.execute("""
                SELECT invoice_uuid, folio, issue_date, description, category, item_mxn_total 
                FROM purchase_details 
                ORDER BY issue_date DESC 
                LIMIT 5
            """)
            samples = cursor.fetchall()
            for sample in samples:
                uuid_short = sample[0][:8] + "..."
                desc_short = sample[3][:30] + "..." if len(sample[3]) > 30 else sample[3]
                print(f"   {uuid_short} | {sample[1]} | {sample[2]} | {desc_short} | {sample[4]} | ${sample[5]:,.2f}")
        else:
            print("✅ Purchase Details Table created successfully (empty)")
        
        conn.commit()
        conn.close()
        
        print("\n🎯 Next Steps:")
        print("1. ✅ Local SQLite database now has correct purchase_details structure")
        print("2. 🔄 Fix PostgreSQL connection in .env file")
        print("3. 📤 Run migration: python scripts/06_database/migrate_data.py")
        print("4. 🧪 Test API: python scripts/06_database/test_postgresql_connection.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating purchase_details table: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Creating Local Purchase Details Table")
    print("=" * 50)
    
    if create_purchase_details_table_local():
        print("\n🎉 SUCCESS! Local database is ready for migration.")
    else:
        print("\n❌ FAILED! Check the errors above.") 