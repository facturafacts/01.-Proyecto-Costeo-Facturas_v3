#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CFDI Processing System v4 - Main Entry Point

This is the main entry point for the enhanced CFDI processing system.
It orchestrates the entire workflow from XML parsing to database storage.

Usage:
    python main.py                    # Process all files in inbox
    python main.py --file invoice.xml # Process single file
    python main.py --setup            # Initialize database
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.processing.batch_processor import BatchProcessor
from src.data.database import DatabaseManager
from src.utils.logging_config import setup_logging as configure_logging
from config.settings import get_settings


def setup_database() -> bool:
    """Initialize the database with all tables."""
    try:
        db_manager = DatabaseManager()
        db_manager.initialize_database()
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
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
        description="CFDI Processing System v4 - Enhanced"
    )
    parser.add_argument(
        "--setup", 
        action="store_true", 
        help="Initialize database and setup directories"
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
        logger.info("Initializing database...")
        if setup_database():
            logger.info("Database setup completed successfully")
        else:
            logger.error("Database setup failed")
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