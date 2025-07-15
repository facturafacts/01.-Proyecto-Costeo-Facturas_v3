#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Models for CFDI Processing System v4

This module contains SQLAlchemy ORM models for the enhanced 5-table schema:
1. Invoice - Comprehensive invoice data
2. InvoiceItem - Line items with AI classification
3. ApprovedSku - Human-approved classifications  
4. ProcessingLog - Activity tracking
5. InvoiceMetadata - Simplified view with business logic
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, Numeric, 
    Boolean, ForeignKey, Index, JSON, Float, create_engine,
    Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Create base class
Base = declarative_base()


class Invoice(Base):
    """
    Comprehensive invoice table storing ALL extracted CFDI fields
    """
    __tablename__ = 'invoices'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # SAT Invoice Identification
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    series = Column(String(25), nullable=True)
    folio = Column(String(40), nullable=True, index=True)
    invoice_type = Column(String(1), nullable=False, default='I')
    version = Column(String(10), nullable=False, default='4.0')
    
    # Dates & Timestamps
    issue_date = Column(DateTime, nullable=False, index=True)
    certification_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Issuer (Emisor) Data
    issuer_rfc = Column(String(13), nullable=False, index=True)
    issuer_name = Column(String(254), nullable=True)
    issuer_fiscal_regime = Column(String(10), nullable=True)
    issuer_use_cfdi = Column(String(10), nullable=True)
    issuer_residence = Column(String(3), nullable=True)
    issuer_tax_id = Column(String(30), nullable=True)
    
    # Receiver (Receptor) Data
    receiver_rfc = Column(String(13), nullable=False, index=True)
    receiver_name = Column(String(254), nullable=True)
    receiver_fiscal_address = Column(String(5), nullable=True)
    receiver_residence = Column(String(3), nullable=True)
    receiver_tax_id = Column(String(30), nullable=True)
    receiver_use_cfdi = Column(String(10), nullable=True)
    
    # Payment Information
    payment_method = Column(String(2), nullable=True)
    payment_method_desc = Column(String(100), nullable=True)
    payment_terms = Column(String(10), nullable=True)
    payment_conditions = Column(String(255), nullable=True)
    
    # Currency & Exchange
    currency = Column(String(3), nullable=False, default='MXN')
    exchange_rate = Column(Numeric(15, 6), nullable=True)
    
    # Financial Totals
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    total_discount = Column(Numeric(15, 2), nullable=False, default=0)
    total_transferred_taxes = Column(Numeric(15, 2), nullable=False, default=0)
    total_withheld_taxes = Column(Numeric(15, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Digital Stamp & Certification
    digital_stamp = Column(Text, nullable=True)
    certificate_number = Column(String(50), nullable=True)
    certificate = Column(Text, nullable=True)
    sat_seal = Column(Text, nullable=True)
    sat_certificate = Column(String(50), nullable=True)
    fiscal_folio = Column(String(36), nullable=True)
    stamp_datetime = Column(DateTime, nullable=True)
    
    # Location & Export
    expedition_place = Column(String(5), nullable=True)
    export_operation = Column(String(2), nullable=True)
    confirmation = Column(String(5), nullable=True)
    
    # Processing Metadata
    source_filename = Column(String(255), nullable=True)
    xml_file_size = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)
    processing_status = Column(String(20), nullable=False, default='processed')
    validation_errors = Column(JSON, nullable=True)
    
    # Additional Data
    custom_fields = Column(JSON, nullable=True)
    
    # Relationships
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    processing_logs = relationship("ProcessingLog", back_populates="invoice", cascade="all, delete-orphan")
    invoice_metadata = relationship("InvoiceMetadata", back_populates="invoice", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_invoice_issuer_date', 'issuer_rfc', 'issue_date'),
        Index('idx_invoice_receiver_date', 'receiver_rfc', 'issue_date'),
        Index('idx_invoice_amount_date', 'total_amount', 'issue_date'),
        Index('idx_invoice_status', 'processing_status'),
        Index('idx_invoice_type_date', 'invoice_type', 'issue_date'),
    )


class InvoiceItem(Base):
    """
    Line items with 3-tier P62 classification and enhanced unit handling
    """
    __tablename__ = 'invoice_items'
    
    # Primary Key & Relationships
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id', name='fk_invoice_items_invoice_id', use_alter=True), nullable=False)
    line_number = Column(Integer, nullable=False)
    
    # Item Identification
    product_code = Column(String(50), nullable=True, index=True)
    internal_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=False, index=True)
    
    # Quantities & Units
    quantity = Column(Numeric(15, 6), nullable=False)
    unit_code = Column(String(10), nullable=True)
    unit_description = Column(String(100), nullable=True)
    units_per_package = Column(Numeric(15, 6), nullable=True)  # NEW
    package_description = Column(String(100), nullable=True)   # NEW
    
    # Pricing
    unit_price = Column(Numeric(15, 6), nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)
    discount = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Taxes (Detailed)
    transferred_taxes = Column(JSON, nullable=True)
    withheld_taxes = Column(JSON, nullable=True)
    total_tax_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    # Final Amount
    total_amount = Column(Numeric(15, 2), nullable=False)
    
    # AI CLASSIFICATION (3-Tier P62 System)
    category = Column(String(50), nullable=True, index=True)
    subcategory = Column(String(100), nullable=True)
    sub_sub_category = Column(String(150), nullable=True)
    
    # Unit Standardization
    standardized_unit = Column(String(20), nullable=True)
    standardized_quantity = Column(Numeric(15, 6), nullable=True)   # NEW
    conversion_factor = Column(Numeric(15, 6), nullable=True)       # NEW
    
    # Classification Metadata
    category_confidence = Column(Float, nullable=True)
    classification_source = Column(String(20), nullable=False, default='gemini_api')
    approval_status = Column(String(20), nullable=False, default='pending')
    sku_key = Column(String(255), nullable=True, index=True)
    classification_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Additional Data
    custom_fields = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    
    # Indexes
    __table_args__ = (
        Index('idx_item_invoice_line', 'invoice_id', 'line_number'),
        Index('idx_item_category', 'category'),
        Index('idx_item_sku_key', 'sku_key'),
        Index('idx_item_approval_status', 'approval_status'),
        Index('idx_item_product_code', 'product_code'),
    )


class ApprovedSku(Base):
    """
    Human-approved classifications for fast lookup and consistency
    """
    __tablename__ = 'approved_skus'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # SKU Identification
    sku_key = Column(String(255), unique=True, nullable=False, index=True)
    product_code = Column(String(50), nullable=True, index=True)
    internal_code = Column(String(50), nullable=True)
    normalized_description = Column(Text, nullable=False)
    
    # APPROVED CLASSIFICATION (Human-verified)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(100), nullable=False)
    sub_sub_category = Column(String(150), nullable=False)
    
    # APPROVED UNIT STANDARDIZATION
    standardized_unit = Column(String(20), nullable=False)
    correct_unit_code = Column(String(10), nullable=True)
    units_per_package = Column(Numeric(15, 6), nullable=True)       # NEW
    package_type = Column(String(20), nullable=True)               # NEW
    conversion_notes = Column(String(255), nullable=True)          # NEW
    
    # Approval Metadata
    typical_quantity_range = Column(String(50), nullable=True)
    approved_by = Column(String(100), nullable=False, default='system')
    approval_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, nullable=True)
    
    # Usage Tracking
    usage_count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # Quality Control
    review_status = Column(String(20), nullable=False, default='approved')
    review_notes = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_sku_product_code', 'product_code'),
        Index('idx_sku_category', 'category'),
        Index('idx_sku_usage', 'usage_count'),
        Index('idx_sku_review_status', 'review_status'),
    )


class ProcessingLog(Base):
    """
    Comprehensive logging for debugging and monitoring
    """
    __tablename__ = 'processing_logs'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Optional Foreign Key
    invoice_id = Column(Integer, ForeignKey('invoices.id', name='fk_processing_logs_invoice_id', use_alter=True), nullable=True)
    
    # Log Classification
    log_level = Column(String(10), nullable=False)
    component = Column(String(50), nullable=False)
    operation = Column(String(50), nullable=True)
    
    # Log Content
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Performance Metrics
    execution_time = Column(Float, nullable=True)
    memory_usage = Column(Integer, nullable=True)
    
    # Context Information
    filename = Column(String(255), nullable=True)
    item_line_number = Column(Integer, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="processing_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_log_level_date', 'log_level', 'created_at'),
        Index('idx_log_component_date', 'component', 'created_at'),
        Index('idx_log_invoice', 'invoice_id'),
        Index('idx_log_operation', 'operation'),
    )


class InvoiceMetadata(Base):
    """
    Simplified invoice data with currency conversion and payment term logic
    """
    __tablename__ = 'invoice_metadata'
    
    # Primary Key & Relationship
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id', name='fk_invoice_metadata_invoice_id', use_alter=True), unique=True, nullable=False)
    
    # Basic Invoice Info
    uuid = Column(String(36), nullable=False)
    folio = Column(String(40), nullable=True)
    issue_date = Column(Date, nullable=False)
    
    # Companies (Simplified)
    issuer_rfc = Column(String(13), nullable=False, index=True)
    issuer_name = Column(String(100), nullable=True)
    receiver_rfc = Column(String(13), nullable=False, index=True)
    receiver_name = Column(String(100), nullable=True)
    
    # Currency Handling with Business Logic
    original_currency = Column(String(3), nullable=False, default='MXN')
    original_total = Column(Numeric(15, 2), nullable=False)
    exchange_rate = Column(Numeric(15, 6), nullable=False, default=1.0)
    mxn_total = Column(Numeric(15, 2), nullable=False)
    
    # Payment Terms (Business Logic)
    payment_method = Column(String(2), nullable=True)
    payment_terms = Column(String(10), nullable=True)
    is_installments = Column(Boolean, nullable=False, default=False)  # PPD
    is_immediate = Column(Boolean, nullable=False, default=True)      # PUE
    
    # Quick Stats
    total_items = Column(Integer, nullable=False, default=0)
    total_categories = Column(Integer, nullable=False, default=0)
    avg_confidence = Column(Float, nullable=True)
    
    # Processing Status
    processing_status = Column(String(20), nullable=False, default='completed')
    has_errors = Column(Boolean, nullable=False, default=False)
    error_count = Column(Integer, nullable=False, default=0)
    
    # Business Flags
    is_export = Column(Boolean, nullable=False, default=False)
    has_digital_stamp = Column(Boolean, nullable=False, default=False)
    is_certified = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="invoice_metadata")
    
    # Indexes for Business Queries
    __table_args__ = (
        Index('idx_meta_issuer_date', 'issuer_rfc', 'issue_date'),
        Index('idx_meta_receiver_date', 'receiver_rfc', 'issue_date'),
        Index('idx_meta_payment_terms', 'payment_terms'),
        Index('idx_meta_installments', 'is_installments'),
        Index('idx_meta_currency', 'original_currency'),
        Index('idx_meta_mxn_total', 'mxn_total'),
        Index('idx_meta_status', 'processing_status'),
    ) 

# P62 SALES SYSTEM INTEGRATION - Restaurant Sales Data Models

class ValidationStatus(enum.Enum):
    """Validation status for P62 sales data processing"""
    MATCHED = "matched"
    ORPHANED_COMANDA = "orphaned_comanda"
    ORPHANED_VENTA = "orphaned_venta"
    DUPLICATE = "duplicate"
    DUPLICATE_FOLIO = "duplicate_folio"
    MISMATCH = "mismatch"
    PENDING = "pending"


class SalesOrder(Base):
    """
    P62 Restaurant Sales Orders - Bill/ticket level data
    Integrated with main CFDI system for comprehensive business intelligence
    """
    __tablename__ = 'sales_orders'
    
    id = Column(Integer, primary_key=True, index=True)
    folio_comanda = Column(String, nullable=True, index=True)
    folio_cuenta = Column(String, nullable=True, index=True)
    
    # Dates from the source files
    fecha_apertura = Column(DateTime, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)
    processing_date = Column(Date, nullable=False, index=True)
    
    # Financial totals
    comandas_total = Column(Float, nullable=True)  # Sum from comandas file
    ventas_total = Column(Float, nullable=True)    # Amount from ventas file
    net_sales = Column(Float, nullable=True)
    taxes = Column(Float, nullable=True)
    discounts = Column(Float, nullable=True)
    
    # Validation and quality tracking
    validation_status = Column(Enum(ValidationStatus), default=ValidationStatus.PENDING, index=True)
    duplicate_count = Column(Integer, default=1)
    last_processed = Column(DateTime, nullable=False)
    
    # Staff information
    mesero = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    items = relationship("SalesItem", back_populates="order")
    quality_logs = relationship("SalesQualityLog", back_populates="order")
    
    # Unique constraint for folio + date to prevent duplicates
    __table_args__ = (
        UniqueConstraint('folio_cuenta', 'processing_date', name='uq_sales_folio_date'),
        Index('idx_sales_order_folio_cuenta', 'folio_cuenta'),
        Index('idx_sales_order_processing_date', 'processing_date'),
        Index('idx_sales_order_validation_status', 'validation_status'),
    )


class SalesItem(Base):
    """
    P62 Restaurant Sales Items - Line item level data
    Integrated with main CFDI system for comprehensive business intelligence
    """
    __tablename__ = 'sales_items'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('sales_orders.id', name='fk_sales_items_order_id', use_alter=True), nullable=False)
    
    # Business keys from comandas file
    folio_comanda = Column(String, nullable=True, index=True)  # Can be null since we match by foliocuenta
    folio_cuenta = Column(String, nullable=True)
    orden = Column(Integer, nullable=True)
    clave_producto = Column(String, nullable=True, index=True)
    
    # Product information
    descripcion = Column(String, nullable=False)
    cantidad = Column(Float, nullable=False)
    importe = Column(Float, nullable=False)
    descuento = Column(Float, nullable=True)
    
    # Timestamps
    fecha_apertura = Column(DateTime, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)
    fecha_captura = Column(DateTime, nullable=True)
    
    # Staff
    mesero = Column(String, nullable=True)
    
    # Data processing metadata
    processing_date = Column(Date, nullable=False)
    duplicate_count = Column(Integer, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    order = relationship("SalesOrder", back_populates="items")
    
    # Indexes
    __table_args__ = (
        Index('idx_sales_item_order_id', 'order_id'),
        Index('idx_sales_item_folio_comanda', 'folio_comanda'),
        Index('idx_sales_item_clave_producto', 'clave_producto'),
        Index('idx_sales_item_processing_date', 'processing_date'),
    )


class SalesQualityLog(Base):
    """
    P62 Data Quality Tracking - Audit trail for sales data processing
    Integrated with main CFDI system for comprehensive business intelligence
    """
    __tablename__ = 'sales_quality_log'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('sales_orders.id', name='fk_sales_quality_log_order_id', use_alter=True), nullable=True)
    
    # Issue classification
    issue_type = Column(String, nullable=False, index=True)  # DUPLICATE, MISMATCH, ORPHAN, etc.
    severity = Column(String, default="INFO")  # INFO, WARNING, ERROR, CRITICAL
    
    # Details
    description = Column(String, nullable=False)
    source_file = Column(String, nullable=True)  # comandas, ventas
    folio_comanda = Column(String, nullable=True, index=True)
    
    # Values for comparison
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    difference = Column(Float, nullable=True)
    
    # Metadata
    processing_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    order = relationship("SalesOrder", back_populates="quality_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_sales_quality_issue_type', 'issue_type'),
        Index('idx_sales_quality_processing_date', 'processing_date'),
        Index('idx_sales_quality_folio_comanda', 'folio_comanda'),
    ) 