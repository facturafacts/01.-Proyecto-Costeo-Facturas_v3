#!/usr/bin/env python3
"""
PRODUCTION DATABASE SCHEMA VALIDATOR

Connects to the production PostgreSQL database defined in your .env file
and lists all tables found. This is a reliable way to verify that the
deployment and database setup commands have run successfully.
"""

import os
import sys
from pathlib import Path
import logging

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_production_schema():
    """Connects to the database and lists all tables."""
    logger.info("--- Starting Production Schema Validator ---")
    try:
        # --- Configuration ---
        project_root = Path(__file__).parent.parent.parent
        load_dotenv(dotenv_path=project_root / '.env')
        database_url = os.getenv("DATABASE_URL")

        if not database_url or "sqlite" in database_url:
            logger.error("❌ ABORTING: DATABASE_URL is not configured for PostgreSQL in your .env file.")
            sys.exit(1)

        logger.info("Successfully loaded PostgreSQL connection string.")
        
        # --- Database Connection ---
        logger.info(f"Connecting to database at {database_url.split('@')[1].split(':')[0]}...")
        engine = create_engine(database_url)
        
        with engine.connect():
            logger.info("✅ Connection successful.")
            
            # --- Inspect Tables ---
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if not tables:
                logger.warning("⚠️ No tables found in the database. The schema might be empty.")
            else:
                logger.info(f"📊 Found {len(tables)} tables in the production database:")
                for table_name in sorted(tables):
                    logger.info(f"  - {table_name}")
        
        logger.info("--- Schema validation finished ---")

    except SQLAlchemyError as e:
        logger.error(f"❌ A database error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_production_schema() 