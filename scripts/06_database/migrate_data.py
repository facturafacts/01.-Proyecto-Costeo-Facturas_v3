#!/usr/bin/env python3
"""
ONE-TIME DATA MIGRATION SCRIPT

This script migrates all data from the local SQLite database to the production
PostgreSQL database configured in your .env file.

**WARNING**: Run this script only ONCE. Running it multiple times will
create duplicate data in your production database.
"""

import sys
from pathlib import Path
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import json

# Add project root so we can import from src/config etc.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from config.settings import get_settings
from src.utils.logging_config import setup_logging

# --- Configuration ---
# The local SQLite database file to read from
SQLITE_DB_PATH = project_root / 'data' / 'database' / 'cfdi_system_v4.db'

# The tables to migrate, in an order that respects foreign key constraints
TABLES_TO_MIGRATE = [
    'invoices',
    'approved_skus',
    'invoice_items',
    'invoice_metadata',
    'processing_logs'
]

def migrate_data():
    """
    Performs a one-time migration of data from the local SQLite database
    to the production PostgreSQL database defined in the .env file.
    """
    # Setup logging
    setup_logging(get_settings())
    logger = logging.getLogger(__name__)
    
    print("🚀 STARTING DATA MIGRATION PROCESS")
    logger.info("🚀 STARTING DATA MIGRATION PROCESS")

    # --- Get Database URLs ---
    try:
        # Get the PostgreSQL URL from the .env file
        settings = get_settings()
        postgres_url = settings.DATABASE_URL
        if "sqlite" in postgres_url or not postgres_url:
            print("❌ Migration Aborted: Your .env file is not configured for PostgreSQL.")
            print("   Please update DATABASE_URL in your .env file with the PostgreSQL connection string.")
            logger.error("DATABASE_URL in .env file is not a PostgreSQL URL.")
            return

        # Explicitly define the source SQLite URL
        sqlite_url = f"sqlite:///{SQLITE_DB_PATH.resolve()}"
        
        print(f"  - Source (SQLite):      {SQLITE_DB_PATH.name}")
        print(f"  - Destination (Postgres): {postgres_url.split('@')[1].split(':')[0]}") # Hide credentials
        logger.info(f"Source (SQLite): {sqlite_url}")

    except Exception as e:
        print(f"❌ Failed to load settings. Make sure your .env file is correct. Error: {e}")
        logger.error(f"Failed to load settings: {e}")
        return

    # --- Create Database Engines ---
    try:
        print("\nConnecting to databases...")
        logger.info("Connecting to databases...")
        sqlite_engine = create_engine(sqlite_url)
        postgres_engine = create_engine(postgres_url)

        # Test connections
        with sqlite_engine.connect() as conn:
            print("  ✅ Source (SQLite) connection successful.")
            logger.info("Source (SQLite) connection successful.")
        with postgres_engine.connect() as conn:
            print("  ✅ Destination (Postgres) connection successful.")
            logger.info("Destination (Postgres) connection successful.")
            
    except SQLAlchemyError as e:
        print(f"❌ Database connection failed: {e}")
        print("   Please check your DATABASE_URL in the .env file and your internet connection.")
        logger.error(f"Database connection failed: {e}")
        return
        
    # --- Perform Migration ---
    print("\nMigrating tables...")
    logger.info("Migrating tables...")

    total_rows_migrated = 0
    for table_name in TABLES_TO_MIGRATE:
        try:
            print(f"\nProcessing table: '{table_name}'...")
            # 1. Read data from SQLite
            with sqlite_engine.connect() as conn:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            
            if count == 0:
                print(f"  - Skipping, no data found in source table.")
                logger.info(f"Skipping '{table_name}', no data to migrate.")
                continue
                
            print(f"  - Reading {count} rows from source...")
            logger.info(f"Reading {count} rows from SQLite table '{table_name}'...")
            df = pd.read_sql_table(table_name, sqlite_engine)

            # --- FIX: Convert dict columns to JSON strings for PostgreSQL ---
            # Columns that are likely to contain dictionary-like objects
            json_columns = ['transferred_taxes', 'withheld_taxes', 'custom_fields', 'details']
            for col in json_columns:
                if col in df.columns:
                    print(f"  - Converting column '{col}' to JSON strings...")
                    # The apply function will convert each dict to a JSON string.
                    # It handles None values gracefully.
                    df[col] = df[col].apply(lambda x: json.dumps(x) if x is not None and isinstance(x, dict) else x)
            
            # 2. Write data to PostgreSQL
            print(f"  - Writing {len(df)} rows to destination...")
            logger.info(f"Writing {len(df)} rows to PostgreSQL table '{table_name}'...")
            df.to_sql(
                table_name,
                postgres_engine,
                if_exists='append',
                index=False,
                chunksize=1000  # Write in batches for large tables
            )
            total_rows_migrated += len(df)
            print(f"  ✅ Success!")
            logger.info(f"Successfully migrated {len(df)} rows for table '{table_name}'.")

        except Exception as e:
            print(f"❌ FAILED to migrate table '{table_name}': {e}")
            print("   Migration aborted. You may need to manually clean the destination tables before retrying.")
            logger.error(f"FAILED to migrate table '{table_name}': {e}", exc_info=True)
            return

    print("\n🎉 --- DATA MIGRATION COMPLETE! ---")
    print(f"   Total rows migrated across all tables: {total_rows_migrated}")
    print("   Your historical data is now in the cloud PostgreSQL database.")
    print("   You can now run tests against the live API to verify.")
    logger.info(f"🎉 --- DATA MIGRATION COMPLETE! Total rows: {total_rows_migrated} ---")

if __name__ == "__main__":
    migrate_data() 