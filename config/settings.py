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
    
    # Database Configuration
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    
    @property 
    def DATABASE_URL(self) -> str:
        """
        Construct DATABASE_URL from individual components or use direct URL.
        Priority: Direct DATABASE_URL > Individual DB_ components > SQLite fallback
        """
        # Check for direct DATABASE_URL first
        direct_url = os.getenv("DATABASE_URL")
        if direct_url:
            return direct_url
        
        # Check for individual PostgreSQL components
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_NAME") 
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_port = os.getenv("DB_PORT", "5432")
        
        # If all PostgreSQL components are provided, construct URL
        if all([db_host, db_name, db_user, db_pass]):
            return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?sslmode=require"
        
        # Fallback to SQLite for development
        return "sqlite:///data/database/cfdi_system_v4.db"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() in ["dev", "development"]
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() in ["prod", "production"]
    
    def is_using_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""
        return self.DATABASE_URL.startswith("postgresql://")
    
    def validate_required_settings(self) -> list:
        """Validate required settings and return missing ones."""
        missing = []
        
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
            
        return missing

def get_settings():
    """Returns the Settings object instance."""
    return Settings()

# Create settings instance
settings = Settings() 