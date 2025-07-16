#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main FastAPI Application for CFDI Processing System v4

Local API server for serving invoice metadata to Google Sheets.
"""

from fastapi import FastAPI

app = FastAPI(
    title="CFDI Processing System v4 - Minimal Test",
    description="A temporary, minimal API to confirm deployment health.",
    version="0.0.1",
)

@app.get("/", summary="Health Check")
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "API is running!"}

# All other code is temporarily commented out for debugging.
# from fastapi.middleware.cors import CORSMiddleware
# from .endpoints import router as api_router
# from ..utils.logging_config import get_logger

# logger = get_logger(__name__)

# app = FastAPI(
#     title="CFDI Processing System v4",
#     description="API for processing and analyzing CFDI invoices.",
#     version="4.0.0",
# )

# # Configure CORS
# origins = [
#     "http://localhost",
#     "http://localhost:3000",
#     "https://*.google.com",
#     "https://*.gstatic.com",
#     "https://*.googleapis.com",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.on_event("startup")
# async def startup_event():
#     logger.info("🚀 API is starting up...")

# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("🔌 API is shutting down...")

# @app.get("/", summary="Health Check")
# async def read_root():
#     """A simple health check endpoint."""
#     return {"status": "ok", "message": "CFDI API is running!"}

# # Include the API router
# app.include_router(api_router, prefix="/api", tags=["CFDI API"]) 