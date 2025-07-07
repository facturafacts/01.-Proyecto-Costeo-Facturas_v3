#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Setup Script for CFDI Processing System v4

This script initializes the database with all tables and sets up
the necessary directory structure.
"""

import sys
from pathlib import Path

# Add both project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))  # For config module
sys.path.insert(0, str(project_root / "src"))  # For src modules

from data.database import DatabaseManager
from config.settings import get_settings

def main():
    """Setup database and directory structure."""
    print("🚀 Setting up CFDI Processing System v4")
    print("=" * 50)
    
    try:
        # Load settings
        settings = get_settings()
        print(f"Environment: {settings.ENVIRONMENT}")
        
        # Initialize database
        print("\n📊 Initializing database...")
        db_manager = DatabaseManager()
        db_manager.initialize_database()
        print("✅ Database initialized successfully!")
        
        # Verify tables
        print("\n🔍 Verifying tables...")
        
        # Import models to check table creation
        from data.models import Invoice, InvoiceItem, ApprovedSku, ProcessingLog, InvoiceMetadata, SalesOrder, SalesItem, SalesQualityLog
        
        # Try to query each table
        with db_manager.get_session() as session:
            invoice_count = session.query(Invoice).count()
            item_count = session.query(InvoiceItem).count()
            sku_count = session.query(ApprovedSku).count()
            log_count = session.query(ProcessingLog).count()
            metadata_count = session.query(InvoiceMetadata).count()
            
            # P62 Sales tables
            sales_order_count = session.query(SalesOrder).count()
            sales_item_count = session.query(SalesItem).count()
            sales_quality_count = session.query(SalesQualityLog).count()
        
        print(f"   • Invoices: {invoice_count}")
        print(f"   • Invoice Items: {item_count}")
        print(f"   • Approved SKUs: {sku_count}")
        print(f"   • Processing Logs: {log_count}")
        print(f"   • Invoice Metadata: {metadata_count}")
        print(f"   • Sales Orders (P62): {sales_order_count}")
        print(f"   • Sales Items (P62): {sales_item_count}")
        print(f"   • Sales Quality Logs (P62): {sales_quality_count}")
        
        # Directory verification
        print("\n📁 Directory structure:")
        directories = [
            settings.INBOX_PATH,
            settings.PROCESSED_PATH,
            settings.FAILED_PATH,
            settings.LOGS_PATH
        ]
        
        for directory in directories:
            path = Path(directory)
            if path.exists():
                print(f"   ✅ {directory}")
            else:
                print(f"   ❌ {directory} (missing)")
        
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Configure your environment variables in config/.env")
        print("2. Place XML files in data/inbox/")
        print("3. Run: python main.py")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 