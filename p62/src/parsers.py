#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P62 Sales Data Parsers
Handles parsing of Excel files with robust error handling and validation
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def normalize_folio(folio_value):
    """Normalize folio values for consistent matching"""
    if pd.isna(folio_value) or folio_value is None:
        return None
    folio_str = str(folio_value).strip().upper()
    # Remove leading zeros: P077 -> P77
    folio_str = re.sub(r'([A-Z]+)0+(\d+)', r'\1\2', folio_str)
    return folio_str

def read_excel_robust(file_path: Path, header=None):
    """
    Robust Excel file reader that tries multiple engines.
    Handles both old .xls and new .xlsx formats regardless of file extension.
    """
    engines_to_try = ['xlrd', 'openpyxl', 'calamine']
    
    for engine in engines_to_try:
        try:
            df = pd.read_excel(file_path, engine=engine, header=header)
            logger.info(f"Successfully read {file_path} with {engine} engine")
            return df
        except Exception as e:
            logger.debug(f"Failed to read {file_path} with {engine} engine: {e}")
            continue
    
    raise Exception(f"Could not read {file_path} with any available engine")

def parse_comandas_file(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Parse comandas.xls file with proper column mapping and validation.
    
    CRITICAL: This parser correctly identifies foliocuenta as the main bill ID
    and handles the fact that foliocomanda is often NULL.
    """
    logger.info(f"Parsing comandas file: {file_path}")
    
    try:
        # Read Excel file
        df = read_excel_robust(file_path)
        
        # Debug: Show original structure
        logger.info(f"Original columns: {list(df.columns)}")
        logger.info(f"Original shape: {df.shape}")
        
        # Map numeric columns to expected names based on actual structure
        column_mapping = {
            0: 'foliocomanda',     # Column A - often NULL
            1: 'foliocuenta',      # Column B - P134, P133, etc. (MAIN BILL ID!)
            2: 'orden',            # Column C - P12, P13, etc.
            3: 'fechaapertura',    # Column D
            4: 'fechacierre',      # Column E  
            5: 'mesero',           # Column F
            6: 'claveproducto',    # Column G
            7: 'fechacaptura',     # Column H
            8: 'descripcion',      # Column I
            9: 'cantidad',         # Column J
            10: 'descuento',       # Column K
            11: 'importe'          # Column L
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Remove header row if it exists
        if len(df) > 0:
            first_row = df.iloc[0]
            header_keywords = ['foliocuenta', 'foliocomanda', 'claveproducto', 'descripcion', 'importe', 'cantidad']
            if any(str(val).upper() in [kw.upper() for kw in header_keywords] for val in first_row if pd.notna(val)):
                logger.info("Removing header row from data")
                df = df.iloc[1:].reset_index(drop=True)
        
        # Convert data types
        date_columns = ['fechaapertura', 'fechacierre', 'fechacaptura']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        numeric_columns = ['cantidad', 'importe', 'descuento', 'orden']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Normalize folios
        if 'foliocomanda' in df.columns:
            df['foliocomanda_normalized'] = df['foliocomanda'].apply(normalize_folio)
        
        if 'foliocuenta' in df.columns:
            df['foliocuenta_normalized'] = df['foliocuenta'].apply(normalize_folio)
        else:
            raise ValueError("foliocuenta column not found - this is required for processing")
        
        # CRITICAL FIX: Filter on foliocuenta, not foliocomanda
        # Remove rows with missing critical data
        df = df.dropna(subset=['foliocuenta', 'importe', 'cantidad'])
        
        logger.info(f"Successfully parsed {len(df)} comandas rows")
        logger.info(f"Unique bills (foliocuenta): {df['foliocuenta_normalized'].nunique()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to parse comandas file {file_path}: {e}")
        return None

def parse_ventas_file(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Parse VENTAS.XLS file with automatic header detection and column mapping.
    """
    logger.info(f"Parsing ventas file: {file_path}")
    
    try:
        # VENTAS file has report headers, try different header rows
        df = None
        for header_row in [4, 5, 6, 7]:
            try:
                test_df = read_excel_robust(file_path, header=header_row)
                # Check if this looks like actual data
                if any('folio' in str(col).lower() for col in test_df.columns):
                    df = test_df
                    logger.info(f"Found data headers at row {header_row + 1}")
                    break
            except:
                continue
        
        if df is None:
            df = read_excel_robust(file_path, header=4)
        
        logger.info(f"Original ventas columns: {list(df.columns)}")
        
        # Map columns based on known VENTAS.XLS structure
        ventas_column_mapping = {}
        for col in df.columns:
            col_str = str(col).lower()
            if 'folio' in col_str:
                ventas_column_mapping[col] = 'folio'
            elif col_str == 'total':
                ventas_column_mapping[col] = 'total'
            elif 'articulos' in col_str:
                ventas_column_mapping[col] = 'neto'
            elif 'impuesto' in col_str:
                ventas_column_mapping[col] = 'impuestos'
            elif 'descuento' in col_str and 'cortesia' in col_str:
                ventas_column_mapping[col] = 'descuentos'
            elif 'cierre' in col_str:
                ventas_column_mapping[col] = 'cierre'
        
        # Apply column mapping
        if ventas_column_mapping:
            df = df.rename(columns=ventas_column_mapping)
        
        # Convert data types
        date_columns = ['fecha', 'fechaapertura', 'fechacierre', 'cierre']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        numeric_columns = ['neto', 'impuestos', 'descuentos', 'total']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Normalize folios
        if 'folio' in df.columns:
            df['folio_normalized'] = df['folio'].apply(normalize_folio)
        else:
            raise ValueError("folio column not found in ventas file")
        
        logger.info(f"Successfully parsed {len(df)} ventas rows")
        logger.info(f"Unique folios: {df['folio_normalized'].nunique()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to parse ventas file {file_path}: {e}")
        return None

def validate_source_data(comandas_df: pd.DataFrame, ventas_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate source data before processing.
    Returns validation metrics and identifies potential issues.
    """
    validation = {
        'comandas_rows': len(comandas_df),
        'ventas_rows': len(ventas_df),
        'unique_bills': len(comandas_df['foliocuenta_normalized'].dropna().unique()),
        'null_folios': comandas_df['foliocuenta'].isna().sum(),
        'folio_overlap': 0,
        'issues': []
    }
    
    # Check folio overlap
    if 'foliocuenta_normalized' in comandas_df.columns and 'folio_normalized' in ventas_df.columns:
        comandas_folios = set(comandas_df['foliocuenta_normalized'].dropna())
        ventas_folios = set(ventas_df['folio_normalized'].dropna())
        overlap = comandas_folios.intersection(ventas_folios)
        validation['folio_overlap'] = len(overlap)
        
        if len(overlap) == 0:
            validation['issues'].append("No folio overlap detected - files may be from different periods")
    
    # Check for data quality issues
    if validation['null_folios'] > 0:
        validation['issues'].append(f"{validation['null_folios']} rows with null foliocuenta")
    
    if validation['comandas_rows'] == 0:
        validation['issues'].append("No comandas data found")
    
    if validation['ventas_rows'] == 0:
        validation['issues'].append("No ventas data found")
    
    return validation 