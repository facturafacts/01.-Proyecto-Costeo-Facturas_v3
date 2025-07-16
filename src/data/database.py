#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Database Manager for CFDI Processing System v4

Comprehensive database operations with business logic for:
- Currency conversion (MXN = 1.0 automatic)
- Payment terms (PUE vs PPD boolean flags)
- Unit standardization and conversion
- Complete CRUD operations for all 5 tables
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy import create_engine, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Invoice, InvoiceItem, ApprovedSku, ProcessingLog, InvoiceMetadata
from config.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Enhanced database manager with business logic and comprehensive operations.
    """
    
    def __init__(self):
        """Initialize database manager with connection and session factory."""
        self.settings = get_settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
        logger.info("Database Manager initialized")
    
    def _initialize_connection(self) -> None:
        """Initialize database connection and session factory."""
        try:
            # For SQLite, ensure the database directory exists.
            # This is not needed for PostgreSQL.
            if "sqlite" in self.settings.DATABASE_URL:
                db_path = Path(self.settings.DATABASE_URL.replace('sqlite:///', ''))
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create engine with optimizations.
            # The connect_args are specific to SQLite and should not be used for PostgreSQL.
            connect_args = {}
            if "sqlite" in self.settings.DATABASE_URL:
                connect_args = {"check_same_thread": False, "timeout": 30}

            self.engine = create_engine(
                self.settings.DATABASE_URL,
                echo=self.settings.DATABASE_ECHO,
                pool_pre_ping=True,
                connect_args=connect_args
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info(f"Database connection established: {self.settings.DATABASE_URL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def initialize_database(self) -> None:
        """Create all tables and indexes."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
            
            # Log table information
            with self.get_session() as session:
                for table_name in Base.metadata.tables.keys():
                    try:
                        count = session.execute(f"SELECT COUNT(*) FROM {table_name}").scalar()
                        logger.info(f"Table '{table_name}': {count} records")
                    except Exception:
                        logger.info(f"Table '{table_name}': initialized")
                        
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def save_invoice(self, invoice_data: Dict[str, Any]) -> int:
        """
        Save complete invoice with business logic applied.
        
        Args:
            invoice_data: Complete invoice data dictionary
            
        Returns:
            Created invoice ID
        """
        try:
            with self.get_session() as session:
                # Create invoice record
                invoice = self._create_invoice_record(invoice_data)
                session.add(invoice)
                session.flush()  # Get the ID
                
                # Save items with enhanced data
                items_data = invoice_data.get('items', [])
                saved_items = self._save_invoice_items(session, invoice.id, items_data)
                
                # Create metadata with business logic
                metadata = self._create_invoice_metadata(invoice, saved_items, invoice_data)
                session.add(metadata)
                
                # Log successful processing
                self._log_processing_event(
                    session, invoice.id, 'INFO', 'database', 'save_invoice',
                    f"Successfully saved invoice {invoice.uuid} with {len(saved_items)} items"
                )
                
                logger.info(f"Saved invoice {invoice.uuid} (ID: {invoice.id}) with {len(saved_items)} items")
                return invoice.id
                
        except IntegrityError as e:
            logger.error(f"Duplicate invoice or constraint violation: {e}")
            raise ValueError(f"Invoice already exists or data constraint violation: {e}")
        except Exception as e:
            logger.error(f"Error saving invoice: {e}")
            raise
    
    def _create_invoice_record(self, data: Dict[str, Any]) -> Invoice:
        """Create invoice record with all extracted fields."""
        return Invoice(
            # SAT Identification
            uuid=data['uuid'],
            series=data.get('series'),
            folio=data.get('folio'),
            invoice_type=data.get('invoice_type', 'I'),
            version=data.get('version', '4.0'),
            
            # Dates
            issue_date=data['issue_date'],
            certification_date=data.get('certification_date'),
            
            # Issuer Data
            issuer_rfc=data['issuer_rfc'],
            issuer_name=data.get('issuer_name'),
            issuer_fiscal_regime=data.get('issuer_fiscal_regime'),
            issuer_use_cfdi=data.get('issuer_use_cfdi'),
            issuer_residence=data.get('issuer_residence'),
            issuer_tax_id=data.get('issuer_tax_id'),
            
            # Receiver Data
            receiver_rfc=data['receiver_rfc'],
            receiver_name=data.get('receiver_name'),
            receiver_fiscal_address=data.get('receiver_fiscal_address'),
            receiver_residence=data.get('receiver_residence'),
            receiver_tax_id=data.get('receiver_tax_id'),
            receiver_use_cfdi=data.get('receiver_use_cfdi'),
            
            # Payment Information
            payment_method=data.get('payment_method'),
            payment_method_desc=data.get('payment_method_desc'),
            payment_terms=data.get('payment_terms'),
            payment_conditions=data.get('payment_conditions'),
            
            # Currency & Exchange
            currency=data.get('currency', 'MXN'),
            exchange_rate=data.get('exchange_rate'),
            
            # Financial Totals
            subtotal=data.get('subtotal', Decimal('0')),
            total_discount=data.get('total_discount', Decimal('0')),
            total_transferred_taxes=data.get('total_transferred_taxes', Decimal('0')),
            total_withheld_taxes=data.get('total_withheld_taxes', Decimal('0')),
            total_amount=data.get('total_amount', Decimal('0')),
            
            # Digital Stamp
            digital_stamp=data.get('digital_stamp'),
            certificate_number=data.get('certificate_number'),
            certificate=data.get('certificate'),
            sat_seal=data.get('sat_seal'),
            sat_certificate=data.get('sat_certificate'),
            fiscal_folio=data.get('fiscal_folio'),
            stamp_datetime=data.get('stamp_datetime'),
            
            # Location & Export
            expedition_place=data.get('expedition_place'),
            export_operation=data.get('export_operation'),
            confirmation=data.get('confirmation'),
            
            # Processing Metadata
            source_filename=data.get('source_filename'),
            xml_file_size=data.get('xml_file_size'),
            confidence_score=data.get('confidence_score'),
            processing_time=data.get('processing_time'),
            validation_errors=data.get('validation_errors'),
            custom_fields=data.get('custom_fields')
        )
    
    def _save_invoice_items(self, session: Session, invoice_id: int, items_data: List[Dict]) -> List[InvoiceItem]:
        """Save invoice items with enhanced unit and classification data."""
        saved_items = []
        
        for item_data in items_data:
            # Generate SKU key for classification lookup
            sku_key = self._generate_sku_key(
                item_data.get('description', ''),
                item_data.get('product_code', '')
            )
            
            # Check for approved classification
            approved_classification = self._lookup_approved_sku(session, sku_key)
            
            # Create item record
            item = InvoiceItem(
                invoice_id=invoice_id,
                line_number=item_data.get('line_number', len(saved_items) + 1),
                
                # Item Identification
                product_code=item_data.get('product_code'),
                internal_code=item_data.get('internal_code'),
                description=item_data['description'],
                
                # Quantities & Units
                quantity=item_data['quantity'],
                unit_code=item_data.get('unit_code'),
                unit_description=item_data.get('unit_description'),
                units_per_package=item_data.get('units_per_package'),
                package_description=item_data.get('package_description'),
                
                # Pricing
                unit_price=item_data['unit_price'],
                subtotal=item_data['subtotal'],
                discount=item_data.get('discount', Decimal('0')),
                total_tax_amount=item_data.get('total_tax_amount', Decimal('0')),
                total_amount=item_data['total_amount'],
                
                # Taxes
                transferred_taxes=item_data.get('transferred_taxes'),
                withheld_taxes=item_data.get('withheld_taxes'),
                
                # Classification (from approved or pending)
                category=approved_classification.get('category') if approved_classification else None,
                subcategory=approved_classification.get('subcategory') if approved_classification else None,
                sub_sub_category=approved_classification.get('sub_sub_category') if approved_classification else None,
                
                # Unit Standardization
                standardized_unit=approved_classification.get('standardized_unit') if approved_classification else None,
                standardized_quantity=self._calculate_standardized_quantity(
                    item_data.get('quantity'),
                    item_data.get('units_per_package'),
                    approved_classification.get('conversion_factor') if approved_classification else None
                ),
                conversion_factor=approved_classification.get('conversion_factor') if approved_classification else None,
                
                # Classification Metadata
                category_confidence=approved_classification.get('confidence_score') if approved_classification else None,
                classification_source='approved_sku' if approved_classification else 'pending',
                approval_status='approved' if approved_classification else 'pending',
                sku_key=sku_key,
                
                # Additional Data
                custom_fields=item_data.get('custom_fields')
            )
            
            session.add(item)
            saved_items.append(item)
            
            # Update approved SKU usage if found
            if approved_classification:
                self._update_sku_usage(session, sku_key)
        
        return saved_items
    
    def _create_invoice_metadata(self, invoice: Invoice, items: List[InvoiceItem], 
                                data: Dict[str, Any]) -> InvoiceMetadata:
        """Create simplified metadata with business logic."""
        
        # Apply currency conversion logic (MXN = 1.0)
        exchange_rate = Decimal('1.0') if invoice.currency == 'MXN' else (invoice.exchange_rate or Decimal('1.0'))
        mxn_total = invoice.total_amount * exchange_rate
        
        # Apply payment terms logic (PUE vs PPD)
        payment_terms = invoice.payment_terms or 'PUE'
        is_installments = payment_terms == 'PPD'
        is_immediate = payment_terms == 'PUE'
        
        # Calculate item statistics
        total_items = len(items)
        unique_categories = len(set(item.category for item in items if item.category))
        avg_confidence = sum(item.category_confidence or 0 for item in items) / total_items if total_items > 0 else None
        
        # Check for errors
        has_errors = data.get('validation_errors') is not None
        error_count = len(data.get('validation_errors', []))
        
        return InvoiceMetadata(
            invoice_id=invoice.id,
            uuid=invoice.uuid,
            folio=invoice.folio,
            issue_date=invoice.issue_date.date() if invoice.issue_date else None,
            
            # Companies (Simplified)
            issuer_rfc=invoice.issuer_rfc,
            issuer_name=invoice.issuer_name[:100] if invoice.issuer_name else None,
            receiver_rfc=invoice.receiver_rfc,
            receiver_name=invoice.receiver_name[:100] if invoice.receiver_name else None,
            
            # Currency with Business Logic
            original_currency=invoice.currency,
            original_total=invoice.total_amount,
            exchange_rate=exchange_rate,
            mxn_total=mxn_total,
            
            # Payment Terms with Business Logic
            payment_method=invoice.payment_method,
            payment_terms=payment_terms,
            is_installments=is_installments,
            is_immediate=is_immediate,
            
            # Quick Stats
            total_items=total_items,
            total_categories=unique_categories,
            avg_confidence=avg_confidence,
            
            # Processing Status
            processing_status=invoice.processing_status,
            has_errors=has_errors,
            error_count=error_count,
            
            # Business Flags
            is_export=invoice.export_operation is not None,
            has_digital_stamp=invoice.digital_stamp is not None,
            is_certified=invoice.sat_seal is not None
        )
    
    def _generate_sku_key(self, description: str, product_code: str = "") -> str:
        """Generate normalized SKU key for classification lookup."""
        # Normalize description (remove extra spaces, convert to lowercase)
        normalized_desc = " ".join(description.lower().split())
        
        # Combine with product code if available
        if product_code:
            return f"{product_code.upper()}|{normalized_desc}"
        return normalized_desc
    
    def _lookup_approved_sku(self, session: Session, sku_key: str) -> Optional[Dict[str, Any]]:
        """Look up approved classification for SKU key."""
        try:
            approved = session.query(ApprovedSku).filter(
                ApprovedSku.sku_key == sku_key
            ).first()
            
            if approved:
                return {
                    'category': approved.category,
                    'subcategory': approved.subcategory,
                    'sub_sub_category': approved.sub_sub_category,
                    'standardized_unit': approved.standardized_unit,
                    'conversion_factor': approved.units_per_package,
                    'confidence_score': approved.confidence_score
                }
            return None
            
        except Exception as e:
            logger.warning(f"Error looking up approved SKU {sku_key}: {e}")
            return None
    
    def _calculate_standardized_quantity(self, quantity: Optional[Decimal], 
                                       units_per_package: Optional[Decimal],
                                       conversion_factor: Optional[Decimal]) -> Optional[Decimal]:
        """Calculate standardized quantity using conversion factors."""
        if not quantity:
            return None
        
        # Apply package conversion if available
        if units_per_package and units_per_package > 0:
            quantity = quantity * units_per_package
        
        # Apply additional conversion factor if available
        if conversion_factor and conversion_factor > 0:
            quantity = quantity * conversion_factor
        
        return quantity
    
    def _update_sku_usage(self, session: Session, sku_key: str) -> None:
        """Update usage statistics for approved SKU."""
        try:
            sku = session.query(ApprovedSku).filter(
                ApprovedSku.sku_key == sku_key
            ).first()
            
            if sku:
                sku.usage_count += 1
                sku.last_used = datetime.utcnow()
                
        except Exception as e:
            logger.warning(f"Error updating SKU usage for {sku_key}: {e}")
    
    def _log_processing_event(self, session: Session, invoice_id: Optional[int], 
                            level: str, component: str, operation: str, 
                            message: str, details: Optional[Dict] = None) -> None:
        """Log processing event to database."""
        try:
            log = ProcessingLog(
                invoice_id=invoice_id,
                log_level=level,
                component=component,
                operation=operation,
                message=message,
                details=details
            )
            session.add(log)
            
        except Exception as e:
            logger.warning(f"Error logging to database: {e}")
    
    def get_invoice_by_uuid(self, uuid: str) -> Optional[Invoice]:
        """Get invoice by UUID."""
        try:
            with self.get_session() as session:
                return session.query(Invoice).filter(Invoice.uuid == uuid).first()
        except Exception as e:
            logger.error(f"Error getting invoice by UUID {uuid}: {e}")
            return None
    
    def get_pending_items_for_classification(self, limit: int = 100) -> List[InvoiceItem]:
        """Get items that need AI classification."""
        try:
            with self.get_session() as session:
                return session.query(InvoiceItem).filter(
                    InvoiceItem.approval_status == 'pending'
                ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting pending items: {e}")
            return []
    
    def update_item_classification(self, item_id: int, classification: Dict[str, Any]) -> bool:
        """Update item with AI classification results."""
        try:
            with self.get_session() as session:
                item = session.query(InvoiceItem).filter(InvoiceItem.id == item_id).first()
                if not item:
                    return False
                
                # Update classification
                item.category = classification.get('category')
                item.subcategory = classification.get('subcategory')
                item.sub_sub_category = classification.get('sub_sub_category')
                item.category_confidence = classification.get('confidence_score')
                item.classification_source = 'gemini_api'
                item.approval_status = 'classified'
                item.updated_at = datetime.utcnow()
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating item classification {item_id}: {e}")
            return False
    
    def save_approved_sku(self, sku_data: Dict[str, Any]) -> bool:
        """Save human-approved SKU classification."""
        try:
            with self.get_session() as session:
                sku = ApprovedSku(
                    sku_key=sku_data['sku_key'],
                    product_code=sku_data.get('product_code'),
                    internal_code=sku_data.get('internal_code'),
                    normalized_description=sku_data['normalized_description'],
                    
                    # Approved Classification
                    category=sku_data['category'],
                    subcategory=sku_data['subcategory'],
                    sub_sub_category=sku_data['sub_sub_category'],
                    
                    # Unit Standardization
                    standardized_unit=sku_data['standardized_unit'],
                    correct_unit_code=sku_data.get('correct_unit_code'),
                    units_per_package=sku_data.get('units_per_package'),
                    package_type=sku_data.get('package_type'),
                    conversion_notes=sku_data.get('conversion_notes'),
                    
                    # Metadata
                    typical_quantity_range=sku_data.get('typical_quantity_range'),
                    approved_by=sku_data.get('approved_by', 'system'),
                    confidence_score=sku_data.get('confidence_score'),
                    review_notes=sku_data.get('review_notes')
                )
                
                session.add(sku)
                logger.info(f"Saved approved SKU: {sku_data['sku_key']}")
                return True
                
        except IntegrityError as e:
            logger.warning(f"SKU already exists: {sku_data['sku_key']}")
            return False
        except Exception as e:
            logger.error(f"Error saving approved SKU: {e}")
            return False
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        try:
            with self.get_session() as session:
                # Invoice statistics
                total_invoices = session.query(Invoice).count()
                total_items = session.query(InvoiceItem).count()
                pending_items = session.query(InvoiceItem).filter(
                    InvoiceItem.approval_status == 'pending'
                ).count()
                approved_skus = session.query(ApprovedSku).count()
                
                # Financial statistics
                total_mxn = session.query(func.sum(InvoiceMetadata.mxn_total)).scalar() or 0
                avg_invoice_amount = session.query(func.avg(Invoice.total_amount)).scalar() or 0
                
                # Processing status
                successful = session.query(Invoice).filter(
                    Invoice.processing_status == 'processed'
                ).count()
                
                return {
                    'total_invoices': total_invoices,
                    'total_items': total_items,
                    'pending_classification': pending_items,
                    'approved_skus': approved_skus,
                    'total_mxn_value': float(total_mxn),
                    'avg_invoice_amount': float(avg_invoice_amount),
                    'successful_processing': successful,
                    'processing_rate': (successful / total_invoices * 100) if total_invoices > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting processing statistics: {e}")
            return {} 