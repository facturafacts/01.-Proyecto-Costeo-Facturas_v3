#!/usr/bin/env python3
"""
TEMPORARY SCRIPT - CLEAR PRODUCTION DATABASE TABLES

This script connects to the production PostgreSQL database specified in your .env
file and TRUNCATES (empties) the tables that are part of the migration process.

This is necessary to ensure a clean data migration after a failed attempt.
"""

import os
import sys
from pathlib import Path
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# --- Basic Setup ---
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tables to clear, in an order that respects foreign key dependencies for truncation
TABLES_TO_TRUNCATE = [
    "purchase_details",  # Clear this first as it depends on invoice_items
    "invoice_metadata",  # Depends on invoices
    "processing_logs",   # Depends on invoices
    "invoice_items",     # Depends on invoices
    "invoices",          # Main table
    "approved_skus"      # Independent table
]

def clear_database_tables():
    """Connects to the database and truncates specified tables."""
    try:
        # --- Configuration ---
        # Load environment variables from the .env file in the project root
        project_root = Path(__file__).parent.parent.parent
        load_dotenv(dotenv_path=project_root / '.env')
        logger.info("Loaded environment variables from .env file.")

        # Get the database URL from environment variables
        database_url = os.getenv("DATABASE_URL")

        if not database_url or "sqlite" in database_url:
            logger.error("❌ ABORTING: DATABASE_URL is not configured for PostgreSQL in your .env file.")
            sys.exit(1)

        logger.info("Successfully loaded PostgreSQL connection string.")
        
        # --- Database Connection ---
        logger.info("Connecting to the production database...")
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            logger.info("✅ Connection successful.")
            
            # --- Truncate Tables ---
            # We use CASCADE to handle foreign key relationships correctly.
            # RESTART IDENTITY resets auto-incrementing counters for a clean slate.
            tables_str = ", ".join(TABLES_TO_TRUNCATE)
            truncate_command = text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;")
            
            logger.info(f"Executing command: TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;")
            
            # TRUNCATE requires a transaction to be committed.
            with connection.begin():
                connection.execute(truncate_command)
            
            logger.info("✅ All specified tables have been successfully cleared.")

    except SQLAlchemyError as e:
        logger.error(f"❌ A database error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("--- Starting Database Clearing Script ---")
    clear_database_tables()
    logger.info("--- Script finished ---")