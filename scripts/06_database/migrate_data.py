#!/usr/bin/env python3
"""
ONE-TIME DATA MIGRATION SCRIPT

This script migrates all data from the local SQLite database to the production
PostgreSQL database configured in your .env file.

**WARNING**: Run this script only ONCE. Running it multiple times will
create duplicate data in your production database. It is recommended to run
the `clear_prod_db.py` script before this one if you have partial data.
"""

import sys
import os
from pathlib import Path
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import json
from dotenv import load_dotenv

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
project_root = Path(__file__).parent.parent.parent
SQLITE_DB_PATH = project_root / 'data' / 'database' / 'cfdi_system_v4.db'
TABLES_TO_MIGRATE = [
    'invoices',
    'approved_skus',
    'invoice_items',
    'invoice_metadata',
    'processing_logs',
    'purchase_details'
]

def migrate_data():
    """Performs a one-time migration from local SQLite to production PostgreSQL."""
    logger.info("🚀 STARTING DATA MIGRATION PROCESS")

    try:
        # Load production DB URL from .env
        load_dotenv(dotenv_path=project_root / '.env')
        postgres_url = os.getenv("DATABASE_URL")
        if not postgres_url or "sqlite" in postgres_url:
            logger.error("❌ ABORTING: DATABASE_URL is not configured for PostgreSQL in your .env file.")
            return

        # Define source and destination engines
        sqlite_url = f"sqlite:///{SQLITE_DB_PATH.resolve()}"
        sqlite_engine = create_engine(sqlite_url)
        postgres_engine = create_engine(postgres_url)
        
        logger.info(f"Source (SQLite):      {SQLITE_DB_PATH.name}")
        logger.info(f"Destination (Postgres): {postgres_url.split('@')[1].split(':')[0]}")

        for table_name in TABLES_TO_MIGRATE:
            logger.info(f"--- Migrating table: {table_name} ---")
            
            if not sqlite_engine.dialect.has_table(sqlite_engine.connect(), table_name):
                logger.warning(f"  - Skipping: Table '{table_name}' not found in source SQLite database.")
                continue

            with sqlite_engine.connect() as connection:
                count = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            
            if count == 0:
                logger.info(f"  - Skipping: Table '{table_name}' is empty.")
                continue
            
            logger.info(f"  - Reading {count} rows from source...")
            df = pd.read_sql_table(table_name, sqlite_engine)

            # --- FIX: Convert dict/list columns to JSON strings for PostgreSQL ---
            # Columns that are likely to contain dictionary-like data
            json_columns = ['transferred_taxes', 'withheld_taxes', 'custom_fields', 'validation_errors', 'details']
            for col in json_columns:
                if col in df.columns:
                    # Check if conversion is needed
                    if any(isinstance(x, (dict, list)) for x in df[col] if x is not None):
                        logger.info(f"    - Converting column '{col}' to JSON string format.")
                        df[col] = df[col].apply(lambda x: json.dumps(x) if x is not None else None)

            logger.info(f"  - Writing {len(df)} rows to destination...")
            df.to_sql(table_name, postgres_engine, if_exists='append', index=False)
            logger.info(f"  - ✅ Successfully migrated {table_name}.")

        logger.info("🎉🎉🎉 DATA MIGRATION COMPLETED SUCCESSFULLY! 🎉🎉🎉")

    except SQLAlchemyError as e:
        logger.error(f"❌ A database error occurred during migration: {e}")
        logger.error("   Please check your database connections and table schemas.")
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    migrate_data() 