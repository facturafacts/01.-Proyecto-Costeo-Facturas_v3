#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main FastAPI Application for CFDI Processing System v4

Local API server for serving invoice metadata to Google Sheets.
"""

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import router as api_router
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Create main router
router = APIRouter()

# Include the API router
router.include_router(api_router)

app = FastAPI(
    title="CFDI Processing System v4",
    description="API for processing and analyzing CFDI invoices.",
    version="4.0.0",
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://*.google.com",
    "https://*.gstatic.com",
    "https://script.google.com",
    "https://script.googleusercontent.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 API is starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 API is shutting down...")

# Include the main API router
app.include_router(router, prefix="/api/v1")

@app.get("/", summary="Health Check")
def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to the CFDI Processing API v4"} 