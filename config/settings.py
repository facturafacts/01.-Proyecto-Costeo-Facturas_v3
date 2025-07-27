#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralized Settings Management for CFDI Processing System v4.

Loads configuration from environment variables to ensure a secure and flexible
deployment across different environments (development, testing, production).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

class Settings:
    """Enhanced settings class for CFDI Processing System v4."""
    
    # Environment Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_TIMEOUT: int = int(os.getenv("GEMINI_TIMEOUT", "30"))
    GEMINI_MAX_RETRIES: int = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/database/cfdi_system_v4.db")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    
    # File Paths
    INBOX_PATH: str = os.getenv("INBOX_PATH", "data/inbox")
    PROCESSED_PATH: str = os.getenv("PROCESSED_PATH", "data/processed") 
    FAILED_PATH: str = os.getenv("FAILED_PATH", "data/failed")
    LOGS_PATH: str = os.getenv("LOGS_PATH", "logs")
    
    # P62 Configuration
    P62_CATEGORIES_PATH: str = os.getenv("P62_CATEGORIES_PATH", "config/p62_categories.json")
    
    # Processing Configuration
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    PROCESSING_TIMEOUT: int = int(os.getenv("PROCESSING_TIMEOUT", "300"))
    
    # Currency Configuration
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "MXN")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # Performance Configuration
    ENABLE_PROFILING: bool = os.getenv("ENABLE_PROFILING", "True").lower() == "true"
    MEMORY_LIMIT_MB: int = int(os.getenv("MEMORY_LIMIT_MB", "512"))
    
    # Security Configuration
    ENCRYPT_LOGS: bool = os.getenv("ENCRYPT_LOGS", "False").lower() == "true"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() in ["dev", "development"]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() in ["prod", "production"]
    
    def validate_required_settings(self) -> list:
        """Validate required settings and return missing ones."""
        missing = []
        
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
            
        return missing

def get_settings():
    """Returns a dictionary of application settings for backward compatibility."""
    settings = Settings()
    return {
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
        "DATABASE_URL": settings.DATABASE_URL,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "LOGS_PATH": settings.LOGS_PATH,
        "LOG_MAX_BYTES": settings.LOG_MAX_BYTES,
        "LOG_BACKUP_COUNT": settings.LOG_BACKUP_COUNT,
        "ENABLE_PROFILING": settings.ENABLE_PROFILING,
        "ENVIRONMENT": settings.ENVIRONMENT,
        "is_development": settings.is_development,
        "DATABASE_ECHO": settings.DATABASE_ECHO,
        "INBOX_PATH": settings.INBOX_PATH,
        "PROCESSED_PATH": settings.PROCESSED_PATH,
        "FAILED_PATH": settings.FAILED_PATH,
        "P62_CATEGORIES_PATH": settings.P62_CATEGORIES_PATH,
        "BATCH_SIZE": settings.BATCH_SIZE,
        "DEFAULT_CURRENCY": settings.DEFAULT_CURRENCY,
    }

# Create settings instance
settings = Settings() 