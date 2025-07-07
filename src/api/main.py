#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main FastAPI Application for CFDI Processing System v4

Local API server for serving invoice metadata to Google Sheets.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .endpoints import router
from config.settings import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="REST API for CFDI invoice metadata export to Google Sheets",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for Google Sheets access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://script.google.com",  # Google Apps Script
        "https://docs.google.com",    # Google Sheets
        "https://sheets.googleapis.com",  # Google Sheets API
        "http://localhost:3000",      # Local development
        "http://127.0.0.1:3000",      # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

# Root endpoint
@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "CFDI Invoice Metadata API",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "invoice_metadata": "/api/invoices/metadata",
            "single_invoice": "/api/invoices/metadata/{uuid}"
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    """
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    """
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API docs available at: http://{settings.API_HOST}:{settings.API_PORT}/docs")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    """
    logger.info("Shutting down CFDI Invoice Metadata API")

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    ) 