#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Module for CFDI Processing System v4

FastAPI-based REST API for serving invoice metadata.
"""

from .main import app
from .endpoints import router

__all__ = ['app', 'router'] 