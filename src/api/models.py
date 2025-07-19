#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Response Models for CFDI Processing System v4

Pydantic models for API request/response serialization.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class InvoiceMetadataResponse(BaseModel):
    """Single invoice metadata response model."""
    
    uuid: str = Field(..., description="Invoice UUID")
    folio: Optional[str] = Field(None, description="Invoice folio number")
    issue_date: date = Field(..., description="Invoice issue date")
    issuer_rfc: str = Field(..., description="Issuer RFC")
    issuer_name: Optional[str] = Field(None, description="Issuer company name")
    receiver_rfc: str = Field(..., description="Receiver RFC")
    receiver_name: Optional[str] = Field(None, description="Receiver company name")
    original_currency: str = Field(..., description="Original currency code")
    original_total: float = Field(..., description="Original total amount")
    mxn_total: float = Field(..., description="Total amount in MXN")
    exchange_rate: float = Field(..., description="Exchange rate to MXN")
    payment_method: Optional[str] = Field(None, description="Payment method code")
    is_installments: bool = Field(..., description="True if payment in installments (PPD)")
    is_immediate: bool = Field(..., description="True if immediate payment (PUE)")
    
    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
            Decimal: float
        }


class InvoiceMetadataListResponse(BaseModel):
    """Response model for list of invoice metadata."""
    
    success: bool = Field(True, description="Operation success status")
    data: List[InvoiceMetadataResponse] = Field(..., description="List of invoice metadata")
    count: int = Field(..., description="Number of records returned")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


# ========================================
# DASHBOARD MODELS
# ========================================

class SalesWeeklySummaryResponse(BaseModel):
    """Sales weekly summary response model."""
    
    week_start_date: date = Field(..., description="Week start date")
    week_end_date: date = Field(..., description="Week end date")
    total_revenue: float = Field(..., description="Total revenue for the week")
    total_orders: int = Field(..., description="Total orders for the week")
    total_items_sold: float = Field(..., description="Total items sold")
    avg_order_value: float = Field(..., description="Average order value")
    unique_products: int = Field(..., description="Number of unique products sold")
    growth_rate: Optional[float] = Field(None, description="Growth rate vs previous week")
    
    class Config:
        from_attributes = True


class ProductPerformanceResponse(BaseModel):
    """Product performance response model."""
    
    product_code: str = Field(..., description="Product code")
    product_description: str = Field(..., description="Product description")
    weekly_revenue: float = Field(..., description="Weekly revenue")
    weekly_quantity: float = Field(..., description="Weekly quantity sold")
    total_revenue: float = Field(..., description="Total revenue all time")
    total_quantity: float = Field(..., description="Total quantity all time")
    avg_price: float = Field(..., description="Average price per unit")
    revenue_rank: Optional[int] = Field(None, description="Revenue ranking")
    
    class Config:
        from_attributes = True


class ExpenseCategoryResponse(BaseModel):
    """Expense category response model."""
    
    category: str = Field(..., description="Main category")
    subcategory: str = Field(..., description="Subcategory")
    sub_sub_category: str = Field(..., description="Sub-subcategory")
    weekly_spend: float = Field(..., description="Weekly spending")
    monthly_spend: float = Field(..., description="Monthly spending")
    yearly_spend: float = Field(..., description="Yearly spending")
    total_spend: float = Field(..., description="Total spending all time")
    item_count: int = Field(..., description="Number of items")
    invoice_count: int = Field(..., description="Number of invoices")
    last_purchase_date: Optional[date] = Field(None, description="Last purchase date")
    category_rank: Optional[int] = Field(None, description="Category ranking by weekly spend")
    
    class Config:
        from_attributes = True


class SupplierAnalysisResponse(BaseModel):
    """Supplier analysis response model."""
    
    supplier_rfc: str = Field(..., description="Supplier RFC")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    category: str = Field(..., description="Product category")
    total_amount: float = Field(..., description="Total amount spent")
    item_count: int = Field(..., description="Number of items purchased")
    invoice_count: int = Field(..., description="Number of invoices")
    avg_unit_price: float = Field(..., description="Average unit price")
    min_unit_price: Optional[float] = Field(None, description="Minimum unit price")
    max_unit_price: Optional[float] = Field(None, description="Maximum unit price")
    last_purchase_date: Optional[date] = Field(None, description="Last purchase date")
    
    class Config:
        from_attributes = True


class WeeklyKPIsResponse(BaseModel):
    """Weekly KPIs response model."""
    
    week_start_date: date = Field(..., description="Week start date")
    week_end_date: date = Field(..., description="Week end date")
    revenue_per_week: float = Field(..., description="Revenue for the week")
    orders_per_week: int = Field(..., description="Orders for the week")
    revenue_per_order: float = Field(..., description="Average revenue per order")
    items_per_order: float = Field(..., description="Average items per order")
    revenue_per_item: float = Field(..., description="Average revenue per item")
    expenses_per_week: float = Field(..., description="Expenses for the week")
    invoices_per_week: int = Field(..., description="Invoices for the week")
    avg_invoice_size: float = Field(..., description="Average invoice size")
    data_quality_score: Optional[float] = Field(None, description="Data quality score")
    revenue_growth_rate: Optional[float] = Field(None, description="Revenue growth rate")
    expense_growth_rate: Optional[float] = Field(None, description="Expense growth rate")
    
    class Config:
        from_attributes = True


class RealTimeMetricResponse(BaseModel):
    """Real-time metric response model."""
    
    metric_name: str = Field(..., description="Metric name")
    metric_value: Optional[float] = Field(None, description="Metric value")
    metric_text: Optional[str] = Field(None, description="Metric description")
    metric_category: Optional[str] = Field(None, description="Metric category")
    metric_date: Optional[date] = Field(None, description="Metric date")
    last_updated: datetime = Field(..., description="Last updated timestamp")
    
    class Config:
        from_attributes = True


class DashboardSalesResponse(BaseModel):
    """Complete sales dashboard response."""
    
    success: bool = Field(True, description="Operation success status")
    weekly_summary: List[SalesWeeklySummaryResponse] = Field(..., description="Weekly sales summary")
    top_products: List[ProductPerformanceResponse] = Field(..., description="Top performing products")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


class DashboardExpensesResponse(BaseModel):
    """Complete expenses dashboard response."""
    
    success: bool = Field(True, description="Operation success status")
    category_breakdown: List[ExpenseCategoryResponse] = Field(..., description="Expense category breakdown")
    supplier_analysis: List[SupplierAnalysisResponse] = Field(..., description="Supplier analysis")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


class DashboardKPIsResponse(BaseModel):
    """Complete KPIs dashboard response."""
    
    success: bool = Field(True, description="Operation success status")
    weekly_kpis: List[WeeklyKPIsResponse] = Field(..., description="Weekly KPIs")
    real_time_metrics: List[RealTimeMetricResponse] = Field(..., description="Real-time metrics")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


# ========================================
# PURCHASE DETAILS MODELS (NEW)
# ========================================

class PurchaseDetailsResponse(BaseModel):
    """Purchase details response model for Google Sheets export."""
    
    # Invoice Information
    invoice_uuid: str = Field(..., description="Invoice UUID")
    folio: Optional[str] = Field(None, description="Invoice folio")
    issue_date: Optional[date] = Field(None, description="Invoice issue date")
    issuer_rfc: str = Field(..., description="Issuer RFC")
    issuer_name: Optional[str] = Field(None, description="Issuer name")
    receiver_rfc: str = Field(..., description="Receiver RFC")
    receiver_name: Optional[str] = Field(None, description="Receiver name")
    payment_method: Optional[str] = Field(None, description="Payment method")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    currency: str = Field(..., description="Currency")
    exchange_rate: float = Field(..., description="Exchange rate")
    invoice_mxn_total: float = Field(..., description="Invoice total in MXN")
    is_installments: bool = Field(..., description="Is installments (PPD)")
    is_immediate: bool = Field(..., description="Is immediate (PUE)")
    
    # Item Details
    line_number: int = Field(..., description="Line number")
    product_code: Optional[str] = Field(None, description="Product code")
    description: str = Field(..., description="Item description")
    quantity: float = Field(..., description="Quantity")
    unit_code: Optional[str] = Field(None, description="Unit code")
    unit_price: float = Field(..., description="Unit price")
    subtotal: float = Field(..., description="Subtotal")
    discount: float = Field(..., description="Discount")
    total_amount: float = Field(..., description="Total amount")
    total_tax_amount: float = Field(..., description="Total tax amount")
    
    # Unit Conversion
    units_per_package: float = Field(..., description="Units per package")
    standardized_unit: Optional[str] = Field(None, description="Standardized unit")
    standardized_quantity: Optional[float] = Field(None, description="Standardized quantity")
    conversion_factor: float = Field(..., description="Conversion factor")
    
    # AI Classification
    category: Optional[str] = Field(None, description="Category")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    sub_sub_category: Optional[str] = Field(None, description="Sub-subcategory")
    category_confidence: Optional[float] = Field(None, description="Classification confidence")
    classification_source: Optional[str] = Field(None, description="Classification source")
    approval_status: Optional[str] = Field(None, description="Approval status")
    sku_key: Optional[str] = Field(None, description="SKU key")
    
    # MXN Calculations
    item_mxn_total: float = Field(..., description="Item total in MXN")
    standardized_mxn_value: Optional[float] = Field(None, description="Standardized MXN value")
    unit_mxn_price: float = Field(..., description="Unit price in MXN")
    
    # Timestamps
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat() + 'Z',
            Decimal: float
        }


class PurchaseDetailsListResponse(BaseModel):
    """Response model for purchase details list."""
    
    success: bool = Field(True, description="Operation success status")
    data: List[PurchaseDetailsResponse] = Field(..., description="Purchase details list")
    count: int = Field(..., description="Number of records returned")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


class SKUApprovalRequest(BaseModel):
    """Request model for approving a list of SKUs."""
    sku_keys: List[str] = Field(..., description="A list of sku_key strings to be approved.")

class GenericSuccessResponse(BaseModel):
    """A generic success response model."""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    
    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        } 