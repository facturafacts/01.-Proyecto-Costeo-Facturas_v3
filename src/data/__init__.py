#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Package for CFDI Processing System v4

This package contains database models, operations, and data management utilities.
Includes P62 restaurant sales integration.
"""

from .database import DatabaseManager
from .models import (
    Base,
    Invoice,
    InvoiceItem, 
    ApprovedSku,
    ProcessingLog,
    InvoiceMetadata,
    # P62 Sales System Models
    ValidationStatus,
    SalesOrder,
    SalesItem,
    SalesQualityLog
)

__all__ = [
    'DatabaseManager',
    'Base',
    'Invoice', 
    'InvoiceItem',
    'ApprovedSku',
    'ProcessingLog',
    'InvoiceMetadata',
    # P62 Sales System
    'ValidationStatus',
    'SalesOrder',
    'SalesItem',
    'SalesQualityLog'
] 