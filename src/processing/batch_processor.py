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
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal

from config.settings import get_settings
from src.processing.cfdi_parser import CFDIParser
from src.processing.gemini_classifier import GeminiClassifier
from src.data.database import DatabaseManager
from src.data.models import Invoice, InvoiceItem, ProcessingLog, InvoiceMetadata

# Configure logger
logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Complete batch processing pipeline for CFDI files
    
    Features:
    - End-to-end XML processing workflow
    - Error handling and recovery
    - File management (inbox → processed/failed)
    - Progress tracking and logging
    - Performance monitoring
    - Business logic calculations
    """
    
    def __init__(self):
        """Initialize batch processor with all components."""
        self.settings = get_settings()
        
        # Initialize components
        self.parser = CFDIParser()
        self.classifier = GeminiClassifier()
        self.db_manager = DatabaseManager()
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_successfully': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("BatchProcessor initialized successfully")
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.settings.INBOX_PATH,
            self.settings.PROCESSED_PATH,
            self.settings.FAILED_PATH,
            self.settings.LOGS_PATH
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def find_xml_files(self, directory: str) -> List[str]:
        """
        Find all XML files in the specified directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of XML file paths
        """
        xml_files = []
        
        if not os.path.exists(directory):
            logger.warning(f"Directory not found: {directory}")
            return xml_files
        
        for file in os.listdir(directory):
            if file.lower().endswith('.xml'):
                file_path = os.path.join(directory, file)
                
                # Check file size
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                if file_size > self.settings.MAX_FILE_SIZE_MB:
                    logger.warning(f"File too large ({file_size:.1f}MB): {file}")
                    continue
                
                xml_files.append(file_path)
        
        xml_files.sort()  # Process in consistent order
        logger.info(f"Found {len(xml_files)} XML files in {directory}")
        return xml_files
    
    def process_single_file(self, xml_path: str) -> bool:
        """
        Process a single XML file through the complete pipeline.
        
        Args:
            xml_path: Path to XML file
            
        Returns:
            True if successful, False otherwise
        """
        filename = os.path.basename(xml_path)
        start_time = time.time()
        
        logger.info(f"[START] Processing file: {filename}")
        
        try:
            # 1. Parse XML file
            logger.info(f"[PARSE] Parsing XML: {filename}")
            parsed_data = self.parser.parse_xml_file(xml_path)
            
            if not parsed_data:
                raise ValueError("No data extracted from XML file")
            
            # 2. Check for duplicate invoice
            invoice_uuid = parsed_data.get('uuid')
            logger.info(f"[DUPLICATE CHECK] Checking UUID: {invoice_uuid}")
            
            if self._check_duplicate_invoice(invoice_uuid, filename):
                # Handle duplicate detection
                duplicate_info = self._handle_duplicate_invoice(invoice_uuid, filename, parsed_data)
                
                # Log duplicate as "skipped" processing result
                processing_time = time.time() - start_time
                self._log_processing_result(
                    None, filename, False, processing_time, 
                    0, [], f"DUPLICATE: UUID {invoice_uuid} already exists"
                )
                
                logger.warning(f"[SKIPPED] Duplicate invoice {filename} - moved to failed directory")
                return False
            
            # 3. Classify all items
            logger.info(f"[CLASSIFY] Classifying {len(parsed_data.get('items', []))} items")
            classifications = []
            
            for idx, item_data in enumerate(parsed_data.get('items', [])):
                logger.debug(f"  Classifying item {idx + 1}: {item_data.get('description', '')[:50]}...")
                
                classification = self.classifier.classify_item(item_data)
                classifications.append(classification)
            
            # 4. Store in database
            logger.info(f"[STORE] Saving to database")
            invoice_id = self._save_to_database(parsed_data, classifications, filename)
            
            if not invoice_id:
                raise ValueError("Failed to save invoice to database")
            
            # 5. Create metadata record with business logic
            logger.info(f"[METADATA] Creating business metadata")
            self._create_invoice_metadata(invoice_id, parsed_data, classifications)
            
            # 6. Save to purchase_details table for Google Sheets export
            self._save_to_purchase_details(invoice_id, parsed_data, classifications)
            
            # 7. Log success
            processing_time = time.time() - start_time
            self._log_processing_result(
                invoice_id, filename, True, processing_time, 
                len(classifications), classifications
            )
            
            logger.info(f"[SUCCESS] Processed {filename} in {processing_time:.2f}s")
            return True
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"[ERROR] Failed to process {filename}: {e}")
            
            # Log error
            self._log_processing_result(
                None, filename, False, processing_time, 
                0, [], str(e)
            )
            
            return False
    
    def _save_to_database(self, parsed_data: Dict[str, Any], classifications: List[Dict[str, Any]], filename: str) -> Optional[int]:
        """
        Save parsed invoice and classified items to database.
        
        Args:
            parsed_data: Parsed XML data
            classifications: Item classifications
            filename: Source filename
            
        Returns:
            Invoice ID if successful, None otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                # Create Invoice record
                invoice = Invoice(
                    uuid=parsed_data.get('uuid', ''),
                    series=parsed_data.get('series'),
                    folio=parsed_data.get('folio'),
                    invoice_type=parsed_data.get('invoice_type', 'I'),
                    version=parsed_data.get('version', '4.0'),
                    issue_date=self._parse_datetime(parsed_data.get('issue_date')),
                    certification_date=self._parse_datetime(parsed_data.get('certification_date')),
                    
                    # Issuer data
                    issuer_rfc=parsed_data.get('issuer_rfc'),
                    issuer_name=parsed_data.get('issuer_name'),
                    issuer_fiscal_regime=parsed_data.get('issuer_fiscal_regime'),
                    
                    # Receiver data  
                    receiver_rfc=parsed_data.get('receiver_rfc'),
                    receiver_name=parsed_data.get('receiver_name'),
                    receiver_fiscal_address=parsed_data.get('receiver_fiscal_address'),
                    
                    # Payment information
                    payment_method=parsed_data.get('payment_method'),
                    payment_terms=parsed_data.get('payment_terms'),
                    
                    # Currency and totals
                    currency=parsed_data.get('currency', 'MXN'),
                    exchange_rate=self._safe_decimal(parsed_data.get('exchange_rate', 1.0)),
                    subtotal=self._safe_decimal(parsed_data.get('subtotal', 0)),
                    total_discount=self._safe_decimal(parsed_data.get('total_discount', 0)),
                    total_transferred_taxes=self._safe_decimal(parsed_data.get('total_transferred_taxes', 0)),
                    total_withheld_taxes=self._safe_decimal(parsed_data.get('total_withheld_taxes', 0)),
                    total_amount=self._safe_decimal(parsed_data.get('total_amount', 0)),
                    
                    # Digital stamp
                    digital_stamp=parsed_data.get('digital_stamp'),
                    certificate_number=parsed_data.get('certificate_number'),
                    sat_seal=parsed_data.get('sat_seal'),
                    fiscal_folio=parsed_data.get('fiscal_folio'),
                    stamp_datetime=self._parse_datetime(parsed_data.get('stamp_datetime')),
                    
                    # Processing metadata
                    source_filename=filename,
                    xml_file_size=os.path.getsize(os.path.join(self.settings.INBOX_PATH, filename)),
                    processing_status='processed'
                )
                
                session.add(invoice)
                session.flush()  # Get invoice ID
                
                # Create InvoiceItem records with classifications
                total_confidence = 0.0
                gemini_calls = 0
                
                for idx, (item_data, classification) in enumerate(zip(parsed_data.get('items', []), classifications)):
                    # Calculate standardized quantity with safe decimal conversion
                    original_quantity = self._safe_decimal(item_data.get('quantity', 0))
                    units_per_package = self._safe_decimal(classification.get('units_per_package', 1))
                    standardized_quantity = original_quantity * units_per_package
                    
                    invoice_item = InvoiceItem(
                        invoice_id=invoice.id,
                        line_number=idx + 1,
                        product_code=item_data.get('product_code'),
                        description=item_data.get('description', ''),
                        quantity=original_quantity,
                        unit_code=item_data.get('unit_code'),
                        units_per_package=units_per_package,
                        package_description=classification.get('package_type'),
                        unit_price=self._safe_decimal(item_data.get('unit_price', 0)),
                        subtotal=self._safe_decimal(item_data.get('subtotal', 0)),
                        discount=self._safe_decimal(item_data.get('discount', 0)),
                        total_amount=self._safe_decimal(item_data.get('total_amount', 0)),
                        
                        # AI Classification
                        category=classification.get('category'),
                        subcategory=classification.get('subcategory'),
                        sub_sub_category=classification.get('sub_sub_category'),
                        standardized_unit=classification.get('standardized_unit'),
                        standardized_quantity=standardized_quantity,
                        conversion_factor=self._safe_decimal(classification.get('conversion_factor', 1)),
                        
                        # Classification metadata
                        category_confidence=classification.get('confidence', 0.0),
                        classification_source=classification.get('source', 'unknown'),
                        approval_status=classification.get('approval_status', 'pending'),
                        sku_key=classification.get('sku_key'),
                        
                        # Custom fields for additional data
                        custom_fields={
                            'processing_time': classification.get('processing_time', 0.0),
                            'api_attempt': classification.get('api_attempt'),
                            'reasoning': classification.get('reasoning'),
                            'error': classification.get('error')
                        }
                    )
                    
                    session.add(invoice_item)
                    
                    # Track statistics
                    total_confidence += classification.get('confidence', 0.0)
                    if classification.get('source') == 'gemini_api':
                        gemini_calls += 1
                
                # Update invoice with aggregated data
                if len(classifications) > 0:
                    invoice.confidence_score = total_confidence / len(classifications)
                    invoice.processing_time = sum(c.get('processing_time', 0) for c in classifications)
                
                logger.info(f"Saved invoice {invoice.uuid} with {len(classifications)} items (ID: {invoice.id})")
                return invoice.id
                
        except Exception as e:
            logger.error(f"Database save failed: {e}")
            return None
    
    def _create_invoice_metadata(self, invoice_id: int, parsed_data: Dict[str, Any], classifications: List[Dict[str, Any]]) -> None:
        """
        Create invoice metadata record with business logic.
        
        Args:
            invoice_id: Invoice database ID
            parsed_data: Original parsed data
            classifications: Item classifications
        """
        try:
            with self.db_manager.get_session() as session:
                # Calculate currency conversion (MXN = 1.0)
                original_currency = parsed_data.get('currency', 'MXN')
                original_total = self._safe_decimal(parsed_data.get('total_amount', 0))
                exchange_rate = self._safe_decimal(parsed_data.get('exchange_rate', 1.0))
                
                if original_currency == 'MXN':
                    mxn_total = original_total
                    exchange_rate = Decimal('1.0')
                else:
                    mxn_total = original_total * exchange_rate
                
                # Payment terms logic
                payment_terms = parsed_data.get('payment_terms', '')
                is_installments = payment_terms == 'PPD'  # Pago en Parcialidades o Diferido
                is_immediate = payment_terms == 'PUE'     # Pago en Una Sola Exhibición
                
                # Business flags
                is_export = parsed_data.get('export_operation') not in [None, '', '01']
                has_digital_stamp = bool(parsed_data.get('digital_stamp'))
                is_certified = bool(parsed_data.get('certificate_number'))
                
                # Statistics
                total_items = len(classifications)
                unique_categories = len(set(c.get('category') for c in classifications if c.get('category')))
                avg_confidence = sum(c.get('confidence', 0) for c in classifications) / len(classifications) if classifications else 0.0
                error_count = len([c for c in classifications if c.get('error')])
                
                # Parse datetime safely before using it  
                parsed_issue_date = self._parse_datetime(parsed_data.get('issue_date'))
                
                metadata = InvoiceMetadata(
                    invoice_id=invoice_id,
                    uuid=parsed_data.get('uuid', ''),
                    folio=parsed_data.get('folio'),
                    issue_date=parsed_issue_date.date() if parsed_issue_date else None,
                    
                    # Companies
                    issuer_rfc=parsed_data.get('issuer_rfc'),
                    issuer_name=parsed_data.get('issuer_name', '')[:100],  # Truncate for metadata table
                    receiver_rfc=parsed_data.get('receiver_rfc'),
                    receiver_name=parsed_data.get('receiver_name', '')[:100],
                    
                    # Currency with business logic
                    original_currency=original_currency,
                    original_total=original_total,
                    exchange_rate=exchange_rate,
                    mxn_total=mxn_total,
                    
                    # Payment terms with business logic
                    payment_method=parsed_data.get('payment_method'),
                    payment_terms=payment_terms,
                    is_installments=is_installments,
                    is_immediate=is_immediate,
                    
                    # Statistics
                    total_items=total_items,
                    total_categories=unique_categories,
                    avg_confidence=avg_confidence,
                    
                    # Processing status
                    processing_status='completed',
                    has_errors=error_count > 0,
                    error_count=error_count,
                    
                    # Business flags
                    is_export=is_export,
                    has_digital_stamp=has_digital_stamp,
                    is_certified=is_certified
                )
                
                session.add(metadata)
                logger.info(f"Created metadata for invoice ID {invoice_id}")
                
        except Exception as e:
            logger.error(f"Failed to create metadata: {e}")
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse datetime string with robust handling for CFDI formats.
        
        CRITICAL: Never falls back to current time - preserves data integrity.
        
        Args:
            date_str: Date string from CFDI XML
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None
        
        # Handle case where a datetime object is passed instead of string
        if isinstance(date_str, datetime):
            logger.debug(f"Received datetime object instead of string: {date_str}")
            return date_str
        
        # Ensure we have a string
        if not isinstance(date_str, str):
            logger.warning(f"Expected string or datetime, got {type(date_str)}: {date_str}")
            return None
        
        # Clean the date string first
        clean_date = date_str.strip()
        
        # List of common CFDI datetime formats
        datetime_formats = [
            '%Y-%m-%dT%H:%M:%S',           # 2024-03-15T10:30:00 (most common)
            '%Y-%m-%d %H:%M:%S',           # 2024-03-15 10:30:00
            '%Y-%m-%dT%H:%M:%S.%f',        # 2024-03-15T10:30:00.123456
            '%Y-%m-%dT%H:%M:%SZ',          # 2024-03-15T10:30:00Z
            '%Y-%m-%dT%H:%M:%S.%fZ',       # 2024-03-15T10:30:00.123Z
            '%Y-%m-%d',                    # 2024-03-15 (date only)
            '%d/%m/%Y %H:%M:%S',           # 15/03/2024 10:30:00 (Mexican format)
            '%d/%m/%Y',                    # 15/03/2024 (Mexican date only)
        ]
        
        # Remove timezone indicators that Python can't handle easily
        clean_date = clean_date.replace('Z', '').replace('+00:00', '').replace('-06:00', '').replace('-05:00', '')
        
        # Try each format
        for fmt in datetime_formats:
            try:
                parsed_date = datetime.strptime(clean_date, fmt)
                logger.debug(f"Successfully parsed datetime '{date_str}' using format '{fmt}' -> {parsed_date}")
                return parsed_date
            except ValueError:
                continue
        
        # Try fromisoformat as last resort (handles some edge cases)
        try:
            # Clean for fromisoformat
            iso_clean = clean_date.replace('T', ' ').replace('Z', '')
            parsed_date = datetime.fromisoformat(iso_clean)
            logger.debug(f"Successfully parsed datetime '{date_str}' using fromisoformat -> {parsed_date}")
            return parsed_date
        except ValueError:
            pass
        
        # CRITICAL: Do NOT use current time as fallback!
        # Log the error and return None to preserve data integrity
        logger.error(f"DATETIME PARSING FAILED: Could not parse '{date_str}' with any known format")
        logger.error(f"  Original: '{date_str}'")
        logger.error(f"  Cleaned:  '{clean_date}'")
        logger.error(f"  Result:   NULL (preserving data integrity)")
        
        return None  # Let the database handle NULL dates appropriately
    
    def _log_processing_result(self, invoice_id: Optional[int], filename: str, success: bool, 
                             processing_time: float, item_count: int, 
                             classifications: List[Dict[str, Any]], error: str = None) -> None:
        """Log processing result to database."""
        try:
            with self.db_manager.get_session() as session:
                log_level = 'INFO' if success else 'ERROR'
                message = f"{'Successfully processed' if success else 'Failed to process'} {filename}"
                
                log_metadata = {
                    'filename': filename,
                    'processing_time': processing_time,
                    'item_count': item_count,
                    'success': success
                }
                
                if success and classifications:
                    log_metadata.update({
                        'gemini_calls': len([c for c in classifications if c.get('source') == 'gemini_api']),
                        'approved_skus': len([c for c in classifications if c.get('source') == 'approved_sku']),
                        'avg_confidence': sum(c.get('confidence', 0) for c in classifications) / len(classifications)
                    })
                
                if error:
                    log_metadata['error'] = error
                
                log_entry = ProcessingLog(
                    invoice_id=invoice_id,
                    log_level=log_level,
                    component='batch_processor',
                    operation='process_file',
                    message=message,
                    execution_time=processing_time,
                    filename=filename,
                    details=log_metadata
                )
                
                session.add(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log processing result: {e}")
    
    def move_file(self, source_path: str, destination_dir: str) -> bool:
        """
        Move file to destination directory.
        
        Args:
            source_path: Source file path
            destination_dir: Destination directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filename = os.path.basename(source_path)
            destination_path = os.path.join(destination_dir, filename)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(destination_path):
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_{counter}{ext}"
                destination_path = os.path.join(destination_dir, new_filename)
                counter += 1
            
            shutil.move(source_path, destination_path)
            logger.info(f"Moved {filename} to {destination_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file {source_path}: {e}")
            return False
    
    def process_inbox(self) -> Dict[str, Any]:
        """
        Process all XML files in the inbox directory.
        
        Returns:
            Processing statistics
        """
        logger.info(f"[START] Starting inbox processing: {self.settings.INBOX_PATH}")
        
        self.stats['start_time'] = time.time()
        
        # Find XML files
        xml_files = self.find_xml_files(self.settings.INBOX_PATH)
        self.stats['total_files'] = len(xml_files)
        
        if not xml_files:
            logger.info("[INFO] No XML files found in inbox")
            return self.stats
        
        logger.info(f"[FILES] Processing {len(xml_files)} XML files")
        
        # Process each file
        for idx, xml_path in enumerate(xml_files):
            filename = os.path.basename(xml_path)
            
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing {filename} ({idx + 1}/{len(xml_files)})")
            logger.info(f"{'='*80}")
            
            try:
                success = self.process_single_file(xml_path)
                
                if success:
                    # Move to processed
                    self.move_file(xml_path, self.settings.PROCESSED_PATH)
                    self.stats['processed_successfully'] += 1
                else:
                    # Move to failed
                    self.move_file(xml_path, self.settings.FAILED_PATH)
                    self.stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"[ERROR] Unexpected error processing {filename}: {e}")
                self.move_file(xml_path, self.settings.FAILED_PATH)
                self.stats['failed'] += 1
        
        self.stats['end_time'] = time.time()
        total_time = self.stats['end_time'] - self.stats['start_time']
        
        # Final summary
        logger.info(f"\n{'='*80}")
        logger.info(f"FINAL PROCESSING SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total files: {self.stats['total_files']}")
        logger.info(f"Successfully processed: {self.stats['processed_successfully']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Success rate: {(self.stats['processed_successfully']/self.stats['total_files']*100):.1f}%")
        logger.info(f"Total processing time: {total_time:.2f}s")
        logger.info(f"Average time per file: {(total_time/self.stats['total_files']):.2f}s")
        
        return self.stats
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        return {
            **self.stats,
            'classifier_stats': self.classifier.get_classification_statistics()
        }
    
    def _safe_decimal(self, value: Any, default: Decimal = Decimal('0')) -> Decimal:
        """
        Safely convert value to Decimal with proper error handling.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Decimal value or default
        """
        if value is None:
            return default
        
        try:
            # Convert to string first, then to Decimal
            str_value = str(value).strip()
            if not str_value:
                return default
            
            # Handle problematic decimal values by rounding to 6 decimal places
            decimal_value = Decimal(str_value)
            return decimal_value.quantize(Decimal('0.000001'))
            
        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            logger.warning(f"Could not convert '{value}' to Decimal, using default {default}: {e}")
            return default

    def _check_duplicate_invoice(self, uuid: str, filename: str) -> bool:
        """
        Check if invoice with given UUID already exists in database.
        
        Args:
            uuid: Invoice UUID to check
            filename: Source filename for logging
            
        Returns:
            True if duplicate found, False if unique
        """
        if not uuid:
            logger.warning(f"No UUID found in {filename} - processing anyway")
            return False
        
        try:
            with self.db_manager.get_session() as session:
                # Import here to avoid circular imports
                from src.data.models import Invoice
                
                existing_invoice = session.query(Invoice).filter_by(uuid=uuid).first()
                
                if existing_invoice:
                    logger.warning(f"🔄 DUPLICATE DETECTED: Invoice UUID {uuid} already exists (ID: {existing_invoice.id})")
                    logger.warning(f"   Original file: {existing_invoice.source_filename}")
                    logger.warning(f"   Current file: {filename}")
                    logger.warning(f"   Issue date: {existing_invoice.issue_date}")
                    logger.warning(f"   Total amount: ${existing_invoice.total_amount}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking duplicate for UUID {uuid}: {e}")
            # In case of error, allow processing to continue
            return False

    def _handle_duplicate_invoice(self, uuid: str, filename: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle duplicate invoice detection with detailed logging.
        
        Args:
            uuid: Invoice UUID
            filename: Current filename
            parsed_data: Parsed invoice data
            
        Returns:
            Duplicate handling details
        """
        duplicate_info = {
            'uuid': uuid,
            'filename': filename,
            'action': 'skipped',
            'reason': f'Invoice UUID {uuid} already exists in database'
        }
        
        logger.warning(f"📊 DUPLICATE INVOICE DETAILS:")
        logger.warning(f"   UUID: {uuid}")
        logger.warning(f"   Current file: {filename}")
        logger.warning(f"   Issue date: {parsed_data.get('issue_date', 'Unknown')}")
        logger.warning(f"   Issuer: {parsed_data.get('issuer_name', 'Unknown')}")
        logger.warning(f"   Total: {parsed_data.get('total_amount', 'Unknown')}")
        logger.warning(f"   Action: Skipping duplicate file")
        
        return duplicate_info

    def _save_to_purchase_details(self, invoice_id: int, parsed_data: Dict[str, Any], 
                                 classifications: List[Dict[str, Any]]) -> None:
        """
        Save invoice data to purchase_details table for Google Sheets export.
        
        Args:
            invoice_id: Invoice database ID
            parsed_data: Parsed XML data
            classifications: Item classifications
        """
        try:
            logger.info(f"[PURCHASE_DETAILS] Saving to purchase_details table")
            
            with self.db_manager.get_session() as session:
                # Import models to avoid circular imports
                from src.data.models import Invoice, InvoiceMetadata
                
                # Get invoice and metadata info
                invoice = session.get(Invoice, invoice_id)
                metadata = session.query(InvoiceMetadata).filter_by(invoice_id=invoice_id).first()
                
                if not invoice or not metadata:
                    logger.warning(f"Could not find invoice or metadata for ID {invoice_id}")
                    return
                
                # Use direct SQLite connection for purchase_details insert
                import sqlite3
                db_path = self.settings.DATABASE_URL.replace('sqlite:///', '')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                try:
                    # Insert each item into purchase_details
                    for idx, (item_data, classification) in enumerate(zip(parsed_data.get('items', []), classifications)):
                        
                        # Calculate values with safe decimal conversion
                        original_quantity = float(self._safe_decimal(item_data.get('quantity', 0)))
                        unit_price = float(self._safe_decimal(item_data.get('unit_price', 0)))
                        total_amount = float(self._safe_decimal(item_data.get('total_amount', 0)))
                        subtotal = float(self._safe_decimal(item_data.get('subtotal', 0)))
                        discount = float(self._safe_decimal(item_data.get('discount', 0)))
                        total_tax_amount = float(self._safe_decimal(item_data.get('total_tax_amount', 0)))
                        
                        exchange_rate = float(invoice.exchange_rate or 1.0)
                        units_per_package = float(self._safe_decimal(classification.get('units_per_package', 1)))
                        conversion_factor = float(self._safe_decimal(classification.get('conversion_factor', 1)))
                        
                        # Calculate MXN values
                        item_mxn_total = total_amount * exchange_rate
                        unit_mxn_price = unit_price * exchange_rate
                        standardized_quantity = original_quantity * units_per_package
                        standardized_mxn_value = standardized_quantity * unit_price * exchange_rate if standardized_quantity else None
                        
                        cursor.execute("""
                            INSERT INTO purchase_details (
                                invoice_uuid, folio, issue_date, issuer_rfc, issuer_name,
                                receiver_rfc, receiver_name, payment_method, payment_terms,
                                currency, exchange_rate, invoice_mxn_total, is_installments, is_immediate,
                                line_number, product_code, description, quantity, unit_code,
                                unit_price, subtotal, discount, total_amount, total_tax_amount,
                                units_per_package, standardized_unit, standardized_quantity, conversion_factor,
                                category, subcategory, sub_sub_category, category_confidence,
                                classification_source, approval_status, sku_key,
                                item_mxn_total, standardized_mxn_value, unit_mxn_price,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            invoice.uuid, 
                            invoice.folio, 
                            invoice.issue_date.date() if invoice.issue_date else None,
                            invoice.issuer_rfc, 
                            invoice.issuer_name,
                            invoice.receiver_rfc, 
                            invoice.receiver_name, 
                            invoice.payment_method, 
                            invoice.payment_terms,
                            invoice.currency, 
                            exchange_rate, 
                            float(metadata.mxn_total), 
                            metadata.is_installments, 
                            metadata.is_immediate,
                            idx + 1, 
                            item_data.get('product_code'), 
                            item_data.get('description', ''),
                            original_quantity, 
                            item_data.get('unit_code'), 
                            unit_price,
                            subtotal, 
                            discount,
                            total_amount, 
                            total_tax_amount,
                            units_per_package, 
                            classification.get('standardized_unit'), 
                            standardized_quantity,
                            conversion_factor, 
                            classification.get('category'),
                            classification.get('subcategory'), 
                            classification.get('sub_sub_category'),
                            classification.get('confidence'), 
                            classification.get('source'),
                            classification.get('approval_status', 'pending'), 
                            classification.get('sku_key'),
                            item_mxn_total, 
                            standardized_mxn_value, 
                            unit_mxn_price,
                            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                        ))
                    
                    conn.commit()
                    logger.info(f"[PURCHASE_DETAILS] Saved {len(classifications)} items to purchase_details table")
                    
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error(f"[PURCHASE_DETAILS] Failed to save to purchase_details table: {e}")
            # Don't raise exception - this shouldn't stop the main processing 