#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Processor for CFDI Processing System v4

Orchestrates the complete end-to-end workflow:
1. Parse XML files using CFDIParser
2. Classify items using GeminiClassifier  
3. Store results using DatabaseManager
4. Handle errors gracefully
5. Move files to appropriate directories

Follows v4 Enhanced Cursor Rules:
- Process files in order: Parse → Extract All → SKU Lookup → AI Classify → Store → Metadata
- Always preserve original XML files
- Move processed files to appropriate directories (processed/failed)
- Log all operations with appropriate levels
- Handle errors gracefully - never lose invoice data
- Create invoice_metadata record with business logic
"""

import os
import time
import logging
import shutil
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from src.data.database import get_session
from src.data.models import Invoice, InvoiceItem, ApprovedSku, ProcessingLog, InvoiceMetadata
from src.processing.cfdi_parser import CFDIParser
from src.processing.gemini_classifier import GeminiClassifier
from config.settings import get_settings

class BatchProcessor:
    """
    Processes a batch of CFDI XML files from a given directory.
    """

    def __init__(self, session: Session = None):
        """
        Initializes the batch processor.
        """
        self.session = session or next(get_session())
        self.settings = get_settings()
        self.parser = CFDIParser()
        self.classifier = GeminiClassifier(session=self.session)
        self.processed_files = 0
        self.failed_files = 0
        self.logger = logging.getLogger(__name__)

    def run(self):
        """
        Executes the batch processing of all XML files in the inbox.
        """
        self.logger.info("Starting batch processing run...")
        xml_files = self._list_inbox_files()

        if not xml_files:
            self.logger.info("No new XML files to process in the inbox.")
            return

        self.logger.info(f"Found {len(xml_files)} XML files to process.")

        for file_path in xml_files:
            try:
                self._process_file(file_path)
                self._move_to_processed(file_path)
                self.processed_files += 1
            except Exception as e:
                self.logger.error(f"Failed to process {os.path.basename(file_path)}: {e}", exc_info=True)
                self._move_to_failed(file_path)
                self.failed_files += 1

        self.logger.info(f"Batch processing finished. Processed: {self.processed_files}, Failed: {self.failed_files}")

    def process_inbox(self):
        """
        Process all files in the inbox directory.
        This method provides compatibility with main.py.
        """
        self.run()

    def _list_inbox_files(self) -> List[str]:
        """
        List all XML files in the inbox directory.
        
        Returns:
            List of file paths for XML files to process
        """
        inbox_path = Path(self.settings.get("INBOX_PATH", "data/inbox"))
        
        if not inbox_path.exists():
            self.logger.warning(f"Inbox directory does not exist: {inbox_path}")
            return []
        
        xml_files = []
        for file_path in inbox_path.glob("*.xml"):
            if file_path.is_file():
                xml_files.append(str(file_path))
        
        return xml_files

    def _move_to_processed(self, file_path: str) -> None:
        """
        Move file from inbox to processed folder.
        
        Args:
            file_path: Path to the file to move
        """
        try:
            processed_path = Path(self.settings.get("PROCESSED_PATH", "data/processed"))
            processed_path.mkdir(parents=True, exist_ok=True)
            
            filename = os.path.basename(file_path)
            destination = processed_path / filename
            
            shutil.move(file_path, destination)
            self.logger.info(f"Moved to processed: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error moving {file_path} to processed: {e}")
            raise

    def _move_to_failed(self, file_path: str) -> None:
        """
        Move file from inbox to failed folder.
        
        Args:
            file_path: Path to the file to move
        """
        try:
            failed_path = Path(self.settings.get("FAILED_PATH", "data/failed"))
            failed_path.mkdir(parents=True, exist_ok=True)
            
            filename = os.path.basename(file_path)
            destination = failed_path / filename
            
            shutil.move(file_path, destination)
            self.logger.info(f"Moved to failed: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error moving {file_path} to failed: {e}")

    def _process_file(self, file_path: str):
        """
        Processes a single XML file.
        """
        self.logger.info(f"Processing file: {os.path.basename(file_path)}")
        
        # 1. Parse the CFDI file
        parsed_data = self.parser.parse_xml_file(file_path)
        if not parsed_data:
            raise ValueError("Failed to parse CFDI file.")

        # 2. Classify items using Gemini
        classified_items = self.classifier.classify_items(parsed_data['items'])
        
        # 3. Save to database
        self._save_to_database(parsed_data, classified_items, file_path)
        
    def _save_to_database(self, parsed_data, classified_items, file_path):
        """
        Saves the processed data to the database.
        """
        try:
            # Create and add the main invoice record
            invoice = Invoice(**{k: v for k, v in parsed_data.items() if k != 'items'})
            self.session.add(invoice)
            self.session.flush() # To get the invoice ID

            # Create and add invoice items
            for item_data in classified_items:
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    **item_data
                )
                self.session.add(invoice_item)
            
            # Create and add invoice metadata
            metadata = InvoiceMetadata(
                invoice_id=invoice.id,
                source_filename=os.path.basename(file_path),
                xml_file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                processing_status='processed',
                # Add other metadata fields as needed
            )
            self.session.add(metadata)

            # Log the processing event
            log_entry = ProcessingLog(
                invoice_id=invoice.id,
                log_level='INFO',
                message=f'Successfully processed {os.path.basename(file_path)}',
            )
            self.session.add(log_entry)
            
            self.session.commit()
            self.logger.info(f"Successfully saved invoice {invoice.uuid} to database.")

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Database error for {os.path.basename(file_path)}: {e}", exc_info=True)
            
            # Log the failure
            log_entry = ProcessingLog(
                log_level='ERROR',
                message=f'Failed to save to database: {os.path.basename(file_path)}. Error: {e}',
            )
            self.session.add(log_entry)
            self.session.commit()
            
            raise # Re-raise the exception to be caught by the run method

    def process_single_file(self, file_path: str) -> bool:
        """
        Process a single XML file.
        
        Args:
            file_path: Path to the XML file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._process_file(file_path)
            return True
        except Exception as e:
            self.logger.error(f"Error processing single file {file_path}: {e}")
            return False 