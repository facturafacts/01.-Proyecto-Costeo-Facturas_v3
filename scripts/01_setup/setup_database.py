#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Setup Script for CFDI Processing System v4

This script initializes the database with all tables and sets up
the necessary directory structure.
"""

import sys
from pathlib import Path
import sqlite3
from sqlalchemy import text

# Add both project root and src to path
# In the Docker container, __file__ is /app/scripts/01_setup/setup_database.py
# The project root is therefore three levels up.
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from data.database import DatabaseManager
from config.settings import get_settings

def create_purchase_details_table(db_manager: DatabaseManager) -> bool:
    """Create the purchase_details table in the production database."""
    print("🛒 Creating Purchase Details Table for Google Sheets Export")
    # This function is simplified for PostgreSQL and does not populate data.
    # The API will serve live data directly from the main tables.
    # We only need the schema for potential compatibility.
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS purchase_details (
            id SERIAL PRIMARY KEY,
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
            invoice_mxn_total DECIMAL(15,2) NOT NULL,
            is_installments BOOLEAN NOT NULL DEFAULT FALSE,
            is_immediate BOOLEAN NOT NULL DEFAULT TRUE,
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
            units_per_package DECIMAL(15,6),
            standardized_unit VARCHAR(20),
            standardized_quantity DECIMAL(15,6),
            conversion_factor DECIMAL(15,6),
            category VARCHAR(50),
            subcategory VARCHAR(100),
            sub_sub_category VARCHAR(150),
            category_confidence DECIMAL(5,2),
            classification_source VARCHAR(20),
            approval_status VARCHAR(20) DEFAULT 'pending',
            sku_key VARCHAR(255),
            item_mxn_total DECIMAL(15,2) NOT NULL,
            standardized_mxn_value DECIMAL(15,2),
            unit_mxn_price DECIMAL(15,6) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """
    
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_purchase_details_issue_date ON purchase_details(issue_date);",
        "CREATE INDEX IF NOT EXISTS idx_purchase_details_issuer ON purchase_details(issuer_rfc);",
        "CREATE INDEX IF NOT EXISTS idx_purchase_details_category ON purchase_details(category);",
        "CREATE INDEX IF NOT EXISTS idx_purchase_details_product ON purchase_details(product_code);",
        "CREATE INDEX IF NOT EXISTS idx_purchase_details_approval ON purchase_details(approval_status);",
        "CREATE INDEX IF NOT EXISTS idx_purchase_details_sku_key ON purchase_details(sku_key);",
        "CREATE INDEX IF NOT EXISTS idx_purchase_details_uuid ON purchase_details(invoice_uuid);"
    ]

    try:
        with db_manager.get_session() as session:
            session.execute(text(create_table_sql))
            for index_sql in create_indexes_sql:
                session.execute(text(index_sql))
            session.commit()
        print("   ✅ Purchase_details table and indexes created successfully!")
        return True
    except Exception as e:
        print(f"   ❌ Failed to create purchase_details table: {e}")
        return False

def check_db_connection(engine):
    """Checks if the database connection is valid."""
    try:
        connection = engine.connect()
        connection.close()
        print("✅ Database connection successful.")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def setup_database(engine):
    """Initializes the database, creating tables and adding default data."""
    print("📊 Initializing database...")
    try:
        # Drop all tables to ensure a clean slate
        print("Dropping all existing tables...")
        Base.metadata.drop_all(engine)
        print("Tables dropped successfully.")
        
        # Create all tables defined in the models
        print("Creating new tables...")
        Base.metadata.create_all(engine)
        print("✅ Tables created successfully.")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        # Re-raise the exception to make the script exit with an error code
        raise

def main():
    """Setup database and directory structure."""
    print("🚀 Setting up CFDI Processing System v4")
    print("==================================================")
    
    # Load environment-specific settings
    settings = get_settings()
    print(f"Environment: {settings.ENVIRONMENT}")
    print()
    
    # Initialize database engine
    engine = get_engine()

    # Check database connection before proceeding
    if not check_db_connection(engine):
        return  # Exit if connection fails

    # Setup database schema and initial data
    setup_database(engine)

if __name__ == "__main__":
    main() 