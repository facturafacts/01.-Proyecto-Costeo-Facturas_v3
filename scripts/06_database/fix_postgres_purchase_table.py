#!/usr/bin/env python3
"""
FIX POSTGRESQL PURCHASE_DETAILS TABLE STRUCTURE

This script completely drops and recreates the purchase_details table in PostgreSQL
with the correct flattened schema for Google Sheets export.

**WARNING**: This will DELETE all existing purchase_details data in PostgreSQL.
Run this BEFORE running migrate_data.py to ensure schema compatibility.
"""

import sys
import os
from pathlib import Path
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_postgres_purchase_table():
    """Fixes the PostgreSQL purchase_details table structure."""
    logger.info("🔧 FIXING POSTGRESQL PURCHASE_DETAILS TABLE STRUCTURE")

    try:
        # Load production DB URL from .env
        project_root = Path(__file__).parent.parent.parent
        load_dotenv(dotenv_path=project_root / '.env')
        postgres_url = os.getenv("DATABASE_URL")
        
        if not postgres_url or "sqlite" in postgres_url:
            logger.error("❌ ABORTING: DATABASE_URL is not configured for PostgreSQL in your .env file.")
            return False

        logger.info(f"Connecting to PostgreSQL at: {postgres_url.split('@')[1].split(':')[0]}")

        # Connect to PostgreSQL
        postgres_engine = create_engine(postgres_url)
        
        with postgres_engine.connect() as connection:
            logger.info("✅ Connected to PostgreSQL database.")
            
            # 1. Check current table structure
            logger.info("🔍 Checking current purchase_details table structure...")
            try:
                result = connection.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'purchase_details' 
                    ORDER BY ordinal_position
                """))
                current_columns = [row[0] for row in result]
                logger.info(f"Current columns: {current_columns}")
            except Exception as e:
                logger.info(f"Table doesn't exist or error checking structure: {e}")
                current_columns = []
            
            # 2. Drop existing purchase_details table (if it exists)
            logger.info("🗑️  Dropping existing purchase_details table...")
            connection.execute(text("DROP TABLE IF EXISTS purchase_details CASCADE"))
            connection.commit()
            logger.info("✅ Old table dropped successfully.")
            
            # 3. Create new purchase_details table with correct structure
            logger.info("📋 Creating new purchase_details table with flattened structure...")
            
            create_table_sql = """
            CREATE TABLE purchase_details (
                -- Primary Key
                id SERIAL PRIMARY KEY,
                
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
                is_installments BOOLEAN NOT NULL DEFAULT FALSE,
                is_immediate BOOLEAN NOT NULL DEFAULT TRUE,
                
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
            """
            
            connection.execute(text(create_table_sql))
            logger.info("✅ Table structure created successfully.")
            
            # 4. Create indexes for performance
            logger.info("🚀 Creating indexes...")
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
                connection.execute(text(index_sql))
                logger.info(f"  - Created index: {index_sql.split('ON')[1].strip()}")
            
            connection.commit()
            
            # 5. Verify the new structure
            logger.info("🔍 Verifying new table structure...")
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'purchase_details' 
                ORDER BY ordinal_position
            """))
            new_columns = [row[0] for row in result]
            logger.info(f"New columns: {new_columns}")
            
            # Check for critical columns
            required_columns = ['invoice_uuid', 'folio', 'issue_date', 'description', 'category']
            missing_columns = [col for col in required_columns if col not in new_columns]
            
            if missing_columns:
                logger.error(f"❌ Missing required columns: {missing_columns}")
                return False
            
            logger.info("✅ All required columns present!")
            
            # 6. Final verification
            result = connection.execute(text("SELECT COUNT(*) FROM purchase_details"))
            count = result.scalar()
            logger.info(f"✅ Table is empty and ready: {count} rows")
            
            logger.info("🎉 PostgreSQL purchase_details table structure fixed successfully!")
            logger.info("📋 Table now has the correct flattened structure for Google Sheets export.")
            
            return True

    except SQLAlchemyError as e:
        logger.error(f"❌ A database error occurred: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    success = fix_postgres_purchase_table()
    if success:
        logger.info("🎉 PostgreSQL purchase_details table is ready for migration!")
        logger.info("💡 Next step: Run 'python scripts/06_database/migrate_data.py'")
    else:
        logger.error("❌ Failed to fix PostgreSQL purchase_details table.")
        sys.exit(1) 