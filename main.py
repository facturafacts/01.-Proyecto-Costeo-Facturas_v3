#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CFDI Processing System v4 - Main Entry Point

This is the main entry point for the enhanced CFDI processing system.
It orchestrates the entire workflow from XML parsing to database storage.

Usage:
    python main.py                    # Process all files in inbox
    python main.py --file invoice.xml # Process single file
    python main.py --setup            # Initialize database + purchase_details table
    python main.py --create-purchase-table # Create/rebuild purchase_details table only
"""

import sys
import argparse
import logging
import sqlite3
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.processing.batch_processor import BatchProcessor
from src.data.database import DatabaseManager
from src.utils.logging_config import setup_logging as configure_logging
from config.settings import get_settings


def create_purchase_details_table() -> bool:
    """Create and populate the purchase_details table for Google Sheets export."""
    try:
        settings = get_settings()
        db_path = Path(settings.DATABASE_URL.replace('sqlite:///', ''))
        
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return False
        
        print("\n🛒 Creating Purchase Details Table for Google Sheets Export")
        print("=" * 70)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Create the purchase_details table
        print("📋 Creating purchase_details table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchase_details (
                -- Unique identifier for each line item
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
        
        # 2. Create indexes for performance
        print("🚀 Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_purchase_details_issue_date ON purchase_details(issue_date)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_details_issuer ON purchase_details(issuer_rfc)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_details_category ON purchase_details(category)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_details_product ON purchase_details(product_code)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_details_approval ON purchase_details(approval_status)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_details_sku_key ON purchase_details(sku_key)",
            "CREATE INDEX IF NOT EXISTS idx_purchase_details_uuid ON purchase_details(invoice_uuid)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # 3. Check if we have existing data to populate
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        if invoice_count > 0:
            print(f"📊 Found {invoice_count} existing invoices. Populating purchase_details table...")
            
            # Clear existing data to avoid duplicates
            cursor.execute("DELETE FROM purchase_details")
            
            # Populate the table with existing data
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
                    i.issue_date,
                    i.issuer_rfc,
                    i.issuer_name,
                    i.receiver_rfc,
                    i.receiver_name,
                    i.payment_method,
                    i.payment_terms,
                    i.currency,
                    i.exchange_rate,
                    
                    -- Metadata Business Logic
                    im.mxn_total as invoice_mxn_total,
                    im.is_installments,
                    im.is_immediate,
                    
                    -- Item Details
                    ii.line_number,
                    ii.product_code,
                    ii.description,
                    ii.quantity,
                    ii.unit_code,
                    ii.unit_price,
                    ii.subtotal,
                    ii.discount,
                    ii.total_amount,
                    ii.total_tax_amount,
                    
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
                    ii.classification_source,
                    ii.approval_status,
                    ii.sku_key,
                    
                    -- Calculated Fields
                    (ii.total_amount * i.exchange_rate) as item_mxn_total,
                    CASE 
                        WHEN ii.standardized_quantity IS NOT NULL AND ii.unit_price IS NOT NULL 
                        THEN (ii.standardized_quantity * ii.unit_price * i.exchange_rate)
                        ELSE NULL 
                    END as standardized_mxn_value,
                    (ii.unit_price * i.exchange_rate) as unit_mxn_price
                    
                FROM invoices i
                JOIN invoice_items ii ON i.id = ii.invoice_id
                JOIN invoice_metadata im ON i.id = im.invoice_id
                ORDER BY i.issue_date DESC, ii.line_number
            """)
        else:
            print("📊 No existing invoices found. Purchase_details table created and ready.")
        
        # 4. Get statistics
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
        else:
            print("✅ Purchase Details Table created successfully (empty)")
        
        conn.commit()
        conn.close()
        
        print("\n🎯 Next Steps:")
        print("1. Use this table for Google Sheets export")
        print("2. Query: SELECT * FROM purchase_details ORDER BY issue_date DESC")
        print("3. Process new invoices with: python main.py")
        print("4. Approve SKUs with: python scripts/03_sku_approval/excel_approval.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating purchase_details table: {e}")
        return False


def setup_database() -> bool:
    """Initialize the database with all tables including purchase_details."""
    try:
        print("🔧 Initializing CFDI Database System")
        print("=" * 50)
        
        # 1. Initialize core database tables
        print("1️⃣ Creating core database tables...")
        db_manager = DatabaseManager()
        db_manager.initialize_database()
        print("   ✅ Core tables created successfully!")
        
        # 2. Create purchase_details table
        print("\n2️⃣ Creating purchase_details table...")
        if create_purchase_details_table():
            print("   ✅ Purchase_details table created successfully!")
        else:
            print("   ❌ Failed to create purchase_details table")
            return False
        
        print("\n🎉 Complete Database Setup Finished!")
        print("   🗃️  Core CFDI tables: invoices, invoice_items, approved_skus, processing_logs, invoice_metadata")
        print("   🛒 Google Sheets export table: purchase_details")
        print("   📊 Ready to process invoices and export to Google Sheets")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def process_single_file(file_path: str) -> bool:
    """Process a single XML file."""
    try:
        processor = BatchProcessor()
        result = processor.process_single_file(file_path)
        if result:
            print(f"✅ Successfully processed: {file_path}")
        else:
            print(f"❌ Failed to process: {file_path}")
        return result
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def process_inbox() -> None:
    """Process all files in the inbox directory."""
    try:
        processor = BatchProcessor()
        processor.process_inbox()
        print("✅ Inbox processing completed!")
    except Exception as e:
        print(f"❌ Inbox processing failed: {e}")


def main() -> None:
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="CFDI Processing System v4 - Enhanced with Google Sheets Export"
    )
    parser.add_argument(
        "--setup", 
        action="store_true", 
        help="Initialize database and create all tables including purchase_details"
    )
    parser.add_argument(
        "--create-purchase-table",
        action="store_true",
        help="Create/rebuild the purchase_details table only"
    )
    parser.add_argument(
        "--file", 
        type=str, 
        help="Process a single XML file"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level"
    )

    args = parser.parse_args()

    # Load settings first
    try:
        settings = get_settings()
    except Exception as e:
        print(f"Failed to load settings: {e}")
        sys.exit(1)

    # Setup enhanced logging
    configure_logging(settings)
    logger = logging.getLogger(__name__)
    logger.info("CFDI Processing System v4 started")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")

    # Execute based on arguments
    if args.setup:
        logger.info("Initializing complete database system...")
        if setup_database():
            logger.info("Complete database setup completed successfully")
        else:
            logger.error("Database setup failed")
            sys.exit(1)
    
    elif args.create_purchase_table:
        logger.info("Creating purchase_details table...")
        if create_purchase_details_table():
            logger.info("Purchase_details table created successfully")
        else:
            logger.error("Purchase_details table creation failed")
            sys.exit(1)
    
    elif args.file:
        logger.info(f"Processing single file: {args.file}")
        if process_single_file(args.file):
            logger.info("Single file processing completed successfully")
        else:
            logger.error("Single file processing failed")
            sys.exit(1)
    
    else:
        logger.info("Starting inbox processing...")
        process_inbox()
        logger.info("Inbox processing completed")


if __name__ == "__main__":
    main() 