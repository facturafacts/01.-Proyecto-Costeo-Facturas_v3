#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Setup Script for CFDI Processing System v4

This script initializes the database with all tables and sets up
the necessary directory structure.
"""
import logging
import sys
from pathlib import Path

from sqlalchemy.exc import OperationalError

# Add both project root and src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from config.settings import get_settings
from data.database import DatabaseManager  # Import the manager class
from data.models import Base  # Import the Base for metadata operations

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def check_db_connection(engine):
    """Checks if the database connection is valid."""
    try:
        connection = engine.connect()
        connection.close()
        logger.info("✅ Database connection successful.")
        return True
    except OperationalError as e:
        logger.error(f"❌ Database connection failed: {e}", exc_info=True)
        return False


def setup_database(engine):
    """Initializes the database, creating tables and adding default data."""
    logger.info("📊 Initializing database...")
    try:
        # Drop all tables to ensure a clean slate, checking for existence first
        logger.info("Dropping all existing tables...")
        Base.metadata.drop_all(engine, checkfirst=True)
        logger.info("Tables dropped successfully.")
        
        # Create all tables defined in the models
        logger.info("Creating new tables...")
        Base.metadata.create_all(engine)
        logger.info("✅ Tables created successfully.")

    except Exception as e:
        logger.error(f"❌ Setup failed during table creation: {e}", exc_info=True)
        # Re-raise the exception to make the script exit with an error code
        raise


def main():
    """Setup database and directory structure."""
    logger.info("🚀 Setting up CFDI Processing System v4")
    logger.info("==================================================")
    
    # Load environment-specific settings
    settings = get_settings()
    logger.info(f"Environment: {settings.ENVIRONMENT}\n")
    
    # Initialize database manager and get the engine
    db_manager = DatabaseManager()
    engine = db_manager.engine

    # Check database connection before proceeding
    if not check_db_connection(engine):
        logger.error("Aborting setup due to database connection failure.")
        sys.exit(1)
    
    setup_database(engine)


if __name__ == "__main__":
    main() 