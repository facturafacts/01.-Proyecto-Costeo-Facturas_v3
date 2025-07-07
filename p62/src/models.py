from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
import enum
import re

Base = declarative_base()

class ValidationStatus(enum.Enum):
    MATCHED = "matched"
    ORPHANED_COMANDA = "orphaned_comanda"
    ORPHANED_VENTA = "orphaned_venta"
    DUPLICATE = "duplicate"
    DUPLICATE_FOLIO = "duplicate_folio"
    MISMATCH = "mismatch"
    PENDING = "pending"

class SalesOrder(Base):
    """
    Represents a complete order/ticket, identified by folio_comanda.
    This is the main entity that gets matched between comandas and ventas files.
    """
    __tablename__ = 'sales_orders'
    
    id = Column(Integer, primary_key=True, index=True)
    folio_comanda = Column(String, nullable=False, index=True)
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
    
    # Relationships
    items = relationship("SalesItem", back_populates="order")
    quality_logs = relationship("DataQualityLog", back_populates="order")
    
    # Unique constraint for folio + date to prevent duplicates
    __table_args__ = (
        UniqueConstraint('folio_cuenta', 'processing_date', name='uq_folio_date'),
    )

class SalesItem(Base):
    """
    Represents a single line item from comandas.xls with full business context.
    """
    __tablename__ = 'sales_items'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('sales_orders.id'), nullable=False)
    
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
    
    # Relationship
    order = relationship("SalesOrder", back_populates="items")

class DataQualityLog(Base):
    """
    Tracks data quality issues, mismatches, and processing anomalies.
    """
    __tablename__ = 'data_quality_log'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('sales_orders.id'), nullable=True)
    
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
    created_at = Column(DateTime, nullable=False)
    
    # Relationship
    order = relationship("SalesOrder", back_populates="quality_logs") 