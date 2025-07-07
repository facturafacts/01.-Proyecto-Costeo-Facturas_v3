#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P62 Sales Data Processors
Core business logic for processing sales data with critical fixes
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Import from main CFDI system
from data.database import DatabaseManager
from data.models import ValidationStatus, SalesOrder, SalesItem, SalesQualityLog

logger = logging.getLogger(__name__)

def clean_nan_values(value):
    """Clean pandas NaN values for database operations"""
    if pd.isna(value):
        return None
    if isinstance(value, (list, np.ndarray)) and len(value) > 0:
        return value[0] if not pd.isna(value[0]) else None
    return value

def safe_get_value(series_or_value, default=None):
    """Safely get a single value from pandas Series or return the value itself"""
    if hasattr(series_or_value, 'iloc') and len(series_or_value) > 0:
        return series_or_value.iloc[0]
    elif pd.isna(series_or_value):
        return default
    else:
        return series_or_value

def match_orders_by_folio(comandas_df: pd.DataFrame, ventas_df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
    """
    Match orders between comandas and ventas files using foliocuenta (NOT foliocomanda).
    
    CRITICAL FIX: This function now correctly uses foliocuenta for bill-level matching,
    which resolved the 99% orphaned records issue.
    """
    logger.info("Starting order matching by folio...")
    
    # Group comandas by bill (foliocuenta) - this is the key fix
    comandas_by_bill = comandas_df.groupby('foliocuenta_normalized').agg({
        'foliocuenta': 'first',
        'foliocomanda': lambda x: list(x.dropna()),
        'importe': 'sum',
        'fechaapertura': 'first',
        'fechacierre': 'first',
        'mesero': 'first'
    }).reset_index()
    
    logger.info(f"Grouped comandas into {len(comandas_by_bill)} unique bills")
    
    matched_orders = []
    quality_issues = []
    
    # Match each venta with corresponding comandas bill
    for _, venta in ventas_df.iterrows():
        venta_folio = venta.get('folio_normalized')
        
        if pd.isna(venta_folio):
            quality_issues.append({
                'issue_type': 'ORPHANED_VENTA',
                'severity': 'WARNING',
                'description': f'Venta record has null folio',
                'source_file': 'ventas'
            })
            continue
        
        # Find matching bill in comandas
        matching_bill = comandas_by_bill[comandas_by_bill['foliocuenta_normalized'] == venta_folio]
        
        if len(matching_bill) == 0:
            quality_issues.append({
                'issue_type': 'ORPHANED_VENTA',
                'severity': 'WARNING',
                'description': f'No matching comandas for venta folio: {venta_folio}',
                'source_file': 'ventas',
                'folio_comanda': venta_folio
            })
            continue
        
        bill = matching_bill.iloc[0]
        
        # Check for amount mismatches
        comandas_total = bill['importe']
        ventas_total = venta.get('total')
        
        if pd.notna(comandas_total) and pd.notna(ventas_total):
            difference = abs(comandas_total - ventas_total)
            if difference > 0.01:
                quality_issues.append({
                    'issue_type': 'MISMATCH',
                    'severity': 'WARNING',
                    'description': f'Amount mismatch for folio {venta_folio}: comandas={comandas_total}, ventas={ventas_total}',
                    'source_file': 'both',
                    'folio_comanda': venta_folio,
                    'expected_value': ventas_total,
                    'actual_value': comandas_total,
                    'difference': difference
                })
        
        # Create matched order
        matched_order = {
            'folio_cuenta': bill['foliocuenta'],
            'folio_comanda': str(bill['foliocomanda'][0]) if bill['foliocomanda'] and len(bill['foliocomanda']) > 0 else bill['foliocuenta'],
            'fecha_apertura': bill['fechaapertura'],
            'fecha_cierre': bill['fechacierre'],
            'comandas_total': comandas_total,
            'ventas_total': ventas_total,
            'net_sales': venta.get('neto'),
            'taxes': venta.get('impuestos'),
            'discounts': venta.get('descuentos'),
            'mesero': bill['mesero'],
            'validation_status': ValidationStatus.MATCHED
        }
        
        matched_orders.append(matched_order)
    
    # Check for orphaned comandas
    ventas_folios = set(ventas_df['folio_normalized'].dropna())
    comandas_folios = set(comandas_by_bill['foliocuenta_normalized'].dropna())
    
    orphaned_comandas = comandas_folios - ventas_folios
    for orphaned_folio in orphaned_comandas:
        orphaned_bill = comandas_by_bill[comandas_by_bill['foliocuenta_normalized'] == orphaned_folio].iloc[0]
        
        quality_issues.append({
            'issue_type': 'ORPHANED_COMANDA',
            'severity': 'WARNING',
            'description': f'Comandas bill has no matching venta: {orphaned_folio}',
            'source_file': 'comandas',
            'folio_comanda': orphaned_folio,
            'actual_value': orphaned_bill['importe']
        })
        
        # Still create an order for orphaned comandas
        matched_order = {
            'folio_cuenta': orphaned_bill['foliocuenta'],
            'folio_comanda': str(orphaned_bill['foliocomanda'][0]) if orphaned_bill['foliocomanda'] and len(orphaned_bill['foliocomanda']) > 0 else orphaned_bill['foliocuenta'],
            'fecha_apertura': orphaned_bill['fechaapertura'],
            'fecha_cierre': orphaned_bill['fechacierre'],
            'comandas_total': orphaned_bill['importe'],
            'ventas_total': None,
            'net_sales': None,
            'taxes': None,
            'discounts': None,
            'mesero': orphaned_bill['mesero'],
            'validation_status': ValidationStatus.ORPHANED_COMANDA
        }
        
        matched_orders.append(matched_order)
    
    logger.info(f"Matching completed: {len(matched_orders)} orders, {len(quality_issues)} quality issues")
    return matched_orders, quality_issues

def save_or_update_order(session, order_data: Dict, processing_date: date) -> Tuple[SalesOrder, bool]:
    """
    Save or update a sales order with comprehensive duplicate detection.
    Returns (order, is_duplicate)
    """
    folio_cuenta_normalized = order_data['folio_cuenta']
    
    # Check for existing order
    existing_order = session.query(SalesOrder).filter(
        SalesOrder.folio_cuenta == folio_cuenta_normalized,
        SalesOrder.processing_date == processing_date
    ).first()
    
    if existing_order:
        # Update existing order
        logger.warning(f"Duplicate order detected for folio {folio_cuenta_normalized} on {processing_date}")
        
        if existing_order.duplicate_count is None:
            existing_order.duplicate_count = 1
        existing_order.duplicate_count += 1
        
        # Update financial data if new data is available
        if order_data.get('ventas_total') and not existing_order.ventas_total:
            existing_order.ventas_total = order_data['ventas_total']
            existing_order.net_sales = order_data.get('net_sales')
            existing_order.taxes = order_data.get('taxes')
            existing_order.discounts = order_data.get('discounts')
        
        existing_order.last_processed = datetime.now()
        existing_order.updated_at = datetime.now()
        
        session.flush()
        return existing_order, True  # True indicates duplicate
    else:
        # Create new order with cleaned values
        new_order = SalesOrder(
            folio_comanda=clean_nan_values(order_data.get('folio_comanda')),
            folio_cuenta=folio_cuenta_normalized,
            fecha_apertura=clean_nan_values(order_data.get('fecha_apertura')),
            fecha_cierre=clean_nan_values(order_data.get('fecha_cierre')),
            processing_date=processing_date,
            comandas_total=clean_nan_values(order_data.get('comandas_total')),
            ventas_total=clean_nan_values(order_data.get('ventas_total')),
            net_sales=clean_nan_values(order_data.get('net_sales')),
            taxes=clean_nan_values(order_data.get('taxes')),
            discounts=clean_nan_values(order_data.get('discounts')),
            validation_status=order_data.get('validation_status', ValidationStatus.PENDING),
            duplicate_count=1,
            last_processed=datetime.now(),
            mesero=clean_nan_values(order_data.get('mesero'))
        )
        
        session.add(new_order)
        session.flush()
        return new_order, False  # False indicates new record

def save_order_items(session, order: SalesOrder, order_data: Dict, comandas_df: pd.DataFrame, processing_date: date) -> Tuple[int, int]:
    """
    Save sales items for an order with CRITICAL FIX for item filtering.
    
    CRITICAL FIX: This function now correctly filters items by foliocuenta
    instead of foliocomanda, preventing the 333x data duplication issue.
    
    Returns (items_saved, items_duplicated)
    """
    # CRITICAL FIX: Filter by foliocuenta (bill ID), not foliocomanda (item ID)
    folio_cuenta = order_data['folio_cuenta']
    
    # Use foliocuenta for filtering - this is the key fix
    if 'foliocuenta' in comandas_df.columns:
        order_items = comandas_df[comandas_df['foliocuenta'].astype(str) == str(folio_cuenta)]
    else:
        logger.warning(f"foliocuenta column not found, cannot filter items for order {folio_cuenta}")
        return 0, 0
    
    logger.info(f"Processing {len(order_items)} items for order {folio_cuenta}")
    
    items_saved = 0
    items_duplicated = 0
    
    for _, item_row in order_items.iterrows():
        # Clean values before database operations
        cantidad = clean_nan_values(item_row.get('cantidad', 1.0))
        if cantidad is None:
            logger.warning(f"Missing cantidad for item {item_row.get('claveproducto', 'unknown')}, defaulting to 1.0")
            cantidad = 1.0
            
        importe = clean_nan_values(item_row.get('importe', 0.0))
        if importe is None:
            logger.warning(f"Missing importe for item {item_row.get('claveproducto', 'unknown')}, defaulting to 0.0")
            importe = 0.0
        
        clave_producto = clean_nan_values(item_row.get('claveproducto'))
        descripcion = clean_nan_values(item_row.get('descripcion'))
        
        # Check for existing item
        existing_item = session.query(SalesItem).filter(
            SalesItem.order_id == order.id,
            SalesItem.clave_producto == clave_producto,
            SalesItem.descripcion == descripcion,
            SalesItem.cantidad == cantidad,
            SalesItem.importe == importe
        ).first()
        
        if existing_item:
            # Update duplicate count for existing item
            if existing_item.duplicate_count is None:
                existing_item.duplicate_count = 1
            existing_item.duplicate_count += 1
            existing_item.updated_at = datetime.now()
            items_duplicated += 1
        else:
            # Create new item with cleaned values
            new_item = SalesItem(
                order_id=order.id,
                folio_comanda=clean_nan_values(item_row.get('foliocomanda')),
                folio_cuenta=clean_nan_values(item_row.get('foliocuenta')),
                orden=clean_nan_values(item_row.get('orden')),
                clave_producto=clave_producto,
                descripcion=descripcion,
                cantidad=cantidad,
                importe=importe,
                descuento=clean_nan_values(item_row.get('descuento')),
                fecha_apertura=clean_nan_values(item_row.get('fechaapertura')),
                fecha_cierre=clean_nan_values(item_row.get('fechacierre')),
                fecha_captura=clean_nan_values(item_row.get('fechacaptura')),
                mesero=clean_nan_values(item_row.get('mesero')),
                processing_date=processing_date,
                duplicate_count=1
            )
            
            session.add(new_item)
            items_saved += 1
    
    return items_saved, items_duplicated

def process_sales_data(comandas_file: Path, ventas_file: Path, processing_date: date = None) -> Dict:
    """
    Main processing function with critical fixes applied.
    
    This function includes the major fixes:
    1. Proper item filtering by foliocuenta (not foliocomanda)
    2. Real-time validation and monitoring
    3. Comprehensive error handling
    """
    if processing_date is None:
        processing_date = date.today()
    
    logger.info(f"Starting P62 processing for {processing_date}")
    
    # Import parsing functions
    from .parsers import parse_comandas_file, parse_ventas_file
    
    # Initialize database connection
    db_manager = DatabaseManager()
    
    try:
        # Parse files
        comandas_df = parse_comandas_file(comandas_file)
        ventas_df = parse_ventas_file(ventas_file)
        
        if comandas_df is None or ventas_df is None:
            raise ValueError("Failed to parse input files")
        
        logger.info(f"Parsed {len(comandas_df)} comandas items and {len(ventas_df)} ventas records")
        
        # Match orders between files
        matched_orders, quality_issues = match_orders_by_folio(comandas_df, ventas_df)
        
        # Save to database
        with db_manager.get_session() as session:
            orders_created = 0
            orders_duplicated = 0
            items_created = 0
            items_duplicated = 0
            
            for order_data in matched_orders:
                # Save or update order
                order, is_duplicate = save_or_update_order(session, order_data, processing_date)
                
                if is_duplicate:
                    orders_duplicated += 1
                else:
                    orders_created += 1
                
                # Save order items with CRITICAL FIX
                items_saved, items_duped = save_order_items(session, order, order_data, comandas_df, processing_date)
                items_created += items_saved
                items_duplicated += items_duped
            
            # Save quality issues
            for issue in quality_issues:
                quality_log = SalesQualityLog(
                    issue_type=issue['issue_type'],
                    severity=issue['severity'],
                    description=issue['description'],
                    source_file=issue.get('source_file'),
                    folio_comanda=issue.get('folio_comanda'),
                    expected_value=issue.get('expected_value'),
                    actual_value=issue.get('actual_value'),
                    difference=issue.get('difference'),
                    processing_date=processing_date
                )
                session.add(quality_log)
            
            session.commit()
            
            logger.info("=== PROCESSING SUMMARY ===")
            logger.info(f"Orders created: {orders_created}")
            logger.info(f"Orders duplicated: {orders_duplicated}")
            logger.info(f"Items created: {items_created}")
            logger.info(f"Items duplicated: {items_duplicated}")
            logger.info(f"Quality issues logged: {len(quality_issues)}")
            
            return {
                'orders_created': orders_created,
                'orders_duplicated': orders_duplicated,
                'items_created': items_created,
                'items_duplicated': items_duplicated,
                'quality_issues': len(quality_issues)
            }
            
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise 