#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Endpoints for CFDI Processing System v4

FastAPI endpoints for serving invoice metadata.
"""

import logging
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.exc import SQLAlchemyError

from ..data.database import DatabaseManager
from ..data.models import InvoiceMetadata
from .models import (
    InvoiceMetadataResponse, 
    InvoiceMetadataListResponse, 
    ErrorResponse,
    # Purchase Details models (NEW)
    PurchaseDetailsResponse,
    PurchaseDetailsListResponse,
    # Dashboard models
    DashboardSalesResponse,
    DashboardExpensesResponse, 
    DashboardKPIsResponse,
    SalesWeeklySummaryResponse,
    ProductPerformanceResponse,
    ExpenseCategoryResponse,
    SupplierAnalysisResponse,
    WeeklyKPIsResponse,
    RealTimeMetricResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["Invoice Metadata"])

# Database dependency
def get_db_manager():
    """Dependency to get database manager."""
    return DatabaseManager()


@router.get(
    "/invoices/metadata",
    response_model=InvoiceMetadataListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Get Invoice Metadata",
    description="Retrieve invoice metadata with optional filtering"
)
async def get_invoice_metadata(
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of records to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    issuer_rfc: Optional[str] = Query(None, description="Filter by issuer RFC"),
    receiver_rfc: Optional[str] = Query(None, description="Filter by receiver RFC"),
    currency: Optional[str] = Query(None, description="Filter by currency (MXN, USD, etc.)"),
    date_from: Optional[date] = Query(None, description="Filter invoices from this date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter invoices to this date (YYYY-MM-DD)"),
    payment_immediate: Optional[bool] = Query(None, description="Filter by immediate payment (PUE)"),
    payment_installments: Optional[bool] = Query(None, description="Filter by installment payment (PPD)"),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Get invoice metadata with optional filtering.
    
    Returns all invoice metadata records by default, with support for:
    - Pagination (limit/offset)
    - Filtering by issuer, receiver, currency, dates
    - Payment term filtering
    """
    try:
        logger.info(f"API request: limit={limit}, offset={offset}, issuer_rfc={issuer_rfc}")
        
        with db_manager.get_session() as session:
            # Build query
            query = session.query(InvoiceMetadata)
            
            # Apply filters
            if issuer_rfc:
                query = query.filter(InvoiceMetadata.issuer_rfc == issuer_rfc)
            
            if receiver_rfc:
                query = query.filter(InvoiceMetadata.receiver_rfc == receiver_rfc)
            
            if currency:
                query = query.filter(InvoiceMetadata.original_currency == currency)
            
            if date_from:
                query = query.filter(InvoiceMetadata.issue_date >= date_from)
            
            if date_to:
                query = query.filter(InvoiceMetadata.issue_date <= date_to)
            
            if payment_immediate is not None:
                query = query.filter(InvoiceMetadata.is_immediate == payment_immediate)
            
            if payment_installments is not None:
                query = query.filter(InvoiceMetadata.is_installments == payment_installments)
            
            # Order by issue date (newest first)
            query = query.order_by(InvoiceMetadata.issue_date.desc())
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            
            if limit:
                query = query.limit(limit)
            
            # Execute query
            metadata_records = query.all()
            
            # Convert to response format
            invoice_data = []
            for record in metadata_records:
                invoice_item = InvoiceMetadataResponse(
                    uuid=record.uuid,
                    folio=record.folio,
                    issue_date=record.issue_date,
                    issuer_rfc=record.issuer_rfc,
                    issuer_name=record.issuer_name,
                    receiver_rfc=record.receiver_rfc,
                    receiver_name=record.receiver_name,
                    original_currency=record.original_currency,
                    original_total=float(record.original_total),
                    mxn_total=float(record.mxn_total),
                    exchange_rate=float(record.exchange_rate),
                    payment_method=record.payment_method,
                    is_installments=record.is_installments,
                    is_immediate=record.is_immediate
                )
                invoice_data.append(invoice_item)
            
            logger.info(f"Returning {len(invoice_data)} invoice metadata records")
            
            return InvoiceMetadataListResponse(
                success=True,
                data=invoice_data,
                count=len(invoice_data)
            )
            
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_invoice_metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_invoice_metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/invoices/metadata/{uuid}",
    response_model=InvoiceMetadataResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get Single Invoice Metadata",
    description="Retrieve metadata for a specific invoice by UUID"
)
async def get_invoice_metadata_by_uuid(
    uuid: str,
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Get metadata for a specific invoice by UUID.
    """
    try:
        logger.info(f"API request for invoice UUID: {uuid}")
        
        with db_manager.get_session() as session:
            record = session.query(InvoiceMetadata).filter(
                InvoiceMetadata.uuid == uuid
            ).first()
            
            if not record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Invoice with UUID {uuid} not found"
                )
            
            return InvoiceMetadataResponse(
                uuid=record.uuid,
                folio=record.folio,
                issue_date=record.issue_date,
                issuer_rfc=record.issuer_rfc,
                issuer_name=record.issuer_name,
                receiver_rfc=record.receiver_rfc,
                receiver_name=record.receiver_name,
                original_currency=record.original_currency,
                original_total=float(record.original_total),
                mxn_total=float(record.mxn_total),
                exchange_rate=float(record.exchange_rate),
                payment_method=record.payment_method,
                is_installments=record.is_installments,
                is_immediate=record.is_immediate
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_invoice_metadata_by_uuid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_invoice_metadata_by_uuid: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/purchase/details",
    response_model=PurchaseDetailsListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Get Purchase Details",
    description="Retrieve complete purchase details for Google Sheets export"
)
async def get_purchase_details(
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of records"),
    offset: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    category: Optional[str] = Query(None, description="Filter by category"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get complete purchase details for Google Sheets export."""
    try:
        logger.info(f"API request: purchase details, limit={limit}, offset={offset}")
        
        import sqlite3
        
        # Use direct SQLite connection
        conn = sqlite3.connect('data/database/cfdi_system_v4.db')
        cursor = conn.cursor()
        
        try:
            # Build query with filters
            query = """
                SELECT invoice_uuid, folio, issue_date, issuer_rfc, issuer_name,
                       receiver_rfc, receiver_name, payment_method, payment_terms,
                       currency, exchange_rate, invoice_mxn_total, is_installments, is_immediate,
                       line_number, product_code, description, quantity, unit_code,
                       unit_price, subtotal, discount, total_amount, total_tax_amount,
                       units_per_package, standardized_unit, standardized_quantity, conversion_factor,
                       category, subcategory, sub_sub_category, category_confidence,
                       classification_source, approval_status, sku_key,
                       item_mxn_total, standardized_mxn_value, unit_mxn_price,
                       created_at, updated_at
                FROM purchase_details
                WHERE 1=1
            """
            
            params = []
            
            # Apply filters
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if approval_status:
                query += " AND approval_status = ?"
                params.append(approval_status)
            
            if date_from:
                query += " AND issue_date >= ?"
                params.append(date_from.isoformat())
            
            if date_to:
                query += " AND issue_date <= ?"
                params.append(date_to.isoformat())
            
            # Order by date and line number
            query += " ORDER BY issue_date DESC, invoice_uuid, line_number"
            
            # Apply pagination
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            if offset:
                query += " OFFSET ?"
                params.append(offset)
            
            # Execute query
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to response format
            purchase_details = []
            for row in results:
                from datetime import datetime
                purchase_detail = PurchaseDetailsResponse(
                    invoice_uuid=row[0],
                    folio=row[1],
                    issue_date=datetime.fromisoformat(row[2]).date() if row[2] else None,
                    issuer_rfc=row[3],
                    issuer_name=row[4],
                    receiver_rfc=row[5],
                    receiver_name=row[6],
                    payment_method=row[7],
                    payment_terms=row[8],
                    currency=row[9],
                    exchange_rate=float(row[10]),
                    invoice_mxn_total=float(row[11]),
                    is_installments=bool(row[12]),
                    is_immediate=bool(row[13]),
                    line_number=row[14],
                    product_code=row[15],
                    description=row[16],
                    quantity=float(row[17]),
                    unit_code=row[18],
                    unit_price=float(row[19]),
                    subtotal=float(row[20]),
                    discount=float(row[21]),
                    total_amount=float(row[22]),
                    total_tax_amount=float(row[23]),
                    units_per_package=float(row[24]),
                    standardized_unit=row[25],
                    standardized_quantity=float(row[26]) if row[26] else None,
                    conversion_factor=float(row[27]),
                    category=row[28],
                    subcategory=row[29],
                    sub_sub_category=row[30],
                    category_confidence=float(row[31]) if row[31] else None,
                    classification_source=row[32],
                    approval_status=row[33],
                    sku_key=row[34],
                    item_mxn_total=float(row[35]),
                    standardized_mxn_value=float(row[36]) if row[36] else None,
                    unit_mxn_price=float(row[37]),
                    created_at=datetime.fromisoformat(row[38]),
                    updated_at=datetime.fromisoformat(row[39])
                )
                purchase_details.append(purchase_detail)
            
            logger.info(f"Returning {len(purchase_details)} purchase details")
            
            return PurchaseDetailsListResponse(
                success=True,
                data=purchase_details,
                count=len(purchase_details)
            )
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in get_purchase_details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/dashboard/sales",
    response_model=DashboardSalesResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Get Sales Dashboard Data",
    description="Retrieve complete sales dashboard data including weekly summary and top products"
)
async def get_sales_dashboard(
    weeks: Optional[int] = Query(4, ge=1, le=52, description="Number of weeks to include"),
    limit_products: Optional[int] = Query(20, ge=1, le=100, description="Number of top products to return"),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Get complete sales dashboard data.
    """
    try:
        logger.info(f"API request: sales dashboard, weeks={weeks}, limit_products={limit_products}")
        
        import sqlite3
        
        # Use direct SQLite connection for dashboard queries
        conn = sqlite3.connect('data/database/cfdi_system_v4.db')
        cursor = conn.cursor()
        
        try:
            # Get weekly sales summary
            cursor.execute("""
                SELECT week_start_date, week_end_date, total_revenue, total_orders, 
                       total_items_sold, avg_order_value, unique_products, growth_rate
                FROM sales_weekly_summary 
                ORDER BY week_start_date DESC 
                LIMIT ?
            """, (weeks,))
            weekly_results = cursor.fetchall()
            
            weekly_summary = []
            for row in weekly_results:
                weekly_summary.append(SalesWeeklySummaryResponse(
                    week_start_date=row[0],
                    week_end_date=row[1],
                    total_revenue=float(row[2]),
                    total_orders=row[3],
                    total_items_sold=float(row[4]),
                    avg_order_value=float(row[5]),
                    unique_products=row[6],
                    growth_rate=float(row[7]) if row[7] else None
                ))
            
            # Get top products
            cursor.execute("""
                SELECT product_code, product_description, weekly_revenue, weekly_quantity,
                       total_revenue, total_quantity, avg_price, revenue_rank
                FROM sales_product_performance 
                ORDER BY weekly_revenue DESC 
                LIMIT ?
            """, (limit_products,))
            products_results = cursor.fetchall()
            
            top_products = []
            for row in products_results:
                top_products.append(ProductPerformanceResponse(
                    product_code=row[0],
                    product_description=row[1],
                    weekly_revenue=float(row[2]),
                    weekly_quantity=float(row[3]),
                    total_revenue=float(row[4]),
                    total_quantity=float(row[5]),
                    avg_price=float(row[6]),
                    revenue_rank=row[7]
                ))
            
            logger.info(f"Returning {len(weekly_summary)} weeks and {len(top_products)} products")
            
            return DashboardSalesResponse(
                success=True,
                weekly_summary=weekly_summary,
                top_products=top_products
            )
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in get_sales_dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/dashboard/expenses", 
    response_model=DashboardExpensesResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Get Expenses Dashboard Data",
    description="Retrieve complete expenses dashboard data including category breakdown and supplier analysis"
)
async def get_expenses_dashboard(
    limit_categories: Optional[int] = Query(20, ge=1, le=100, description="Number of top expense categories"),
    limit_suppliers: Optional[int] = Query(10, ge=1, le=50, description="Number of top suppliers"),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Get complete expenses dashboard data.
    """
    try:
        logger.info(f"API request: expenses dashboard, categories={limit_categories}, suppliers={limit_suppliers}")
        
        import sqlite3
        
        # Use direct SQLite connection for dashboard queries
        conn = sqlite3.connect('data/database/cfdi_system_v4.db')
        cursor = conn.cursor()
        
        try:
            # Get expense categories
            cursor.execute("""
                SELECT category, subcategory, sub_sub_category, weekly_spend, monthly_spend,
                       yearly_spend, total_spend, item_count, invoice_count, 
                       last_purchase_date, category_rank
                FROM expenses_category_master 
                ORDER BY weekly_spend DESC 
                LIMIT ?
            """, (limit_categories,))
            categories_results = cursor.fetchall()
            
            category_breakdown = []
            for row in categories_results:
                category_breakdown.append(ExpenseCategoryResponse(
                    category=row[0],
                    subcategory=row[1],
                    sub_sub_category=row[2],
                    weekly_spend=float(row[3]),
                    monthly_spend=float(row[4]),
                    yearly_spend=float(row[5]),
                    total_spend=float(row[6]),
                    item_count=row[7],
                    invoice_count=row[8],
                    last_purchase_date=row[9],
                    category_rank=row[10]
                ))
            
            # Get supplier analysis
            cursor.execute("""
                SELECT supplier_rfc, supplier_name, category, total_amount, item_count,
                       invoice_count, avg_unit_price, min_unit_price, max_unit_price,
                       last_purchase_date
                FROM supplier_product_analysis 
                ORDER BY total_amount DESC 
                LIMIT ?
            """, (limit_suppliers,))
            suppliers_results = cursor.fetchall()
            
            supplier_analysis = []
            for row in suppliers_results:
                supplier_analysis.append(SupplierAnalysisResponse(
                    supplier_rfc=row[0],
                    supplier_name=row[1],
                    category=row[2],
                    total_amount=float(row[3]),
                    item_count=row[4],
                    invoice_count=row[5],
                    avg_unit_price=float(row[6]),
                    min_unit_price=float(row[7]) if row[7] else None,
                    max_unit_price=float(row[8]) if row[8] else None,
                    last_purchase_date=row[9]
                ))
            
            logger.info(f"Returning {len(category_breakdown)} categories and {len(supplier_analysis)} suppliers")
            
            return DashboardExpensesResponse(
                success=True,
                category_breakdown=category_breakdown,
                supplier_analysis=supplier_analysis
            )
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in get_expenses_dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/dashboard/kpis",
    response_model=DashboardKPIsResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Get KPIs Dashboard Data", 
    description="Retrieve complete KPIs dashboard data including weekly metrics and real-time indicators"
)
async def get_kpis_dashboard(
    weeks: Optional[int] = Query(8, ge=1, le=52, description="Number of weeks of KPIs to include"),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Get complete KPIs dashboard data.
    """
    try:
        logger.info(f"API request: KPIs dashboard, weeks={weeks}")
        
        import sqlite3
        
        # Use direct SQLite connection for dashboard queries
        conn = sqlite3.connect('data/database/cfdi_system_v4.db')
        cursor = conn.cursor()
        
        try:
            # Get weekly KPIs
            cursor.execute("""
                SELECT week_start_date, week_end_date, revenue_per_week, orders_per_week,
                       revenue_per_order, items_per_order, revenue_per_item, expenses_per_week,
                       invoices_per_week, avg_invoice_size, data_quality_score,
                       revenue_growth_rate, expense_growth_rate
                FROM weekly_kpis 
                ORDER BY week_start_date DESC 
                LIMIT ?
            """, (weeks,))
            kpis_results = cursor.fetchall()
            
            weekly_kpis = []
            for row in kpis_results:
                weekly_kpis.append(WeeklyKPIsResponse(
                    week_start_date=row[0],
                    week_end_date=row[1],
                    revenue_per_week=float(row[2]),
                    orders_per_week=row[3],
                    revenue_per_order=float(row[4]),
                    items_per_order=float(row[5]),
                    revenue_per_item=float(row[6]),
                    expenses_per_week=float(row[7]),
                    invoices_per_week=row[8],
                    avg_invoice_size=float(row[9]),
                    data_quality_score=float(row[10]) if row[10] else None,
                    revenue_growth_rate=float(row[11]) if row[11] else None,
                    expense_growth_rate=float(row[12]) if row[12] else None
                ))
            
            # Get real-time metrics
            cursor.execute("""
                SELECT metric_name, metric_value, metric_text, metric_category,
                       metric_date, last_updated
                FROM real_time_metrics 
                ORDER BY metric_category, metric_name
            """)
            metrics_results = cursor.fetchall()
            
            real_time_metrics = []
            for row in metrics_results:
                real_time_metrics.append(RealTimeMetricResponse(
                    metric_name=row[0],
                    metric_value=float(row[1]) if row[1] else None,
                    metric_text=row[2],
                    metric_category=row[3],
                    metric_date=row[4],
                    last_updated=row[5]
                ))
            
            logger.info(f"Returning {len(weekly_kpis)} weekly KPIs and {len(real_time_metrics)} real-time metrics")
            
            return DashboardKPIsResponse(
                success=True,
                weekly_kpis=weekly_kpis,
                real_time_metrics=real_time_metrics
            )
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in get_kpis_dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health Check",
    description="Check API health and database connectivity"
)
async def health_check(db_manager: DatabaseManager = Depends(get_db_manager)):
    """
    Health check endpoint.
    """
    try:
        # Test database connection
        with db_manager.get_session() as session:
            count = session.query(InvoiceMetadata).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "invoice_count": count,
            "timestamp": date.today().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        ) 