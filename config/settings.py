#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Settings for CFDI Processing System v4

This module handles all configuration settings with environment-specific
support for dev, test, and production environments.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


class Settings:
    """
    Configuration settings with environment support
    """
    
    # Environment
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
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    INBOX_PATH: str = os.getenv("INBOX_PATH", str(PROJECT_ROOT / "data" / "inbox"))
    PROCESSED_PATH: str = os.getenv("PROCESSED_PATH", str(PROJECT_ROOT / "data" / "processed"))
    FAILED_PATH: str = os.getenv("FAILED_PATH", str(PROJECT_ROOT / "data" / "failed"))
    LOGS_PATH: str = os.getenv("LOGS_PATH", str(PROJECT_ROOT / "logs"))
    
    # P62 Configuration
    P62_CATEGORIES_PATH: str = os.getenv("P62_CATEGORIES_PATH", str(PROJECT_ROOT / "config" / "p62_categories.json"))
    
    # Processing Configuration
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    PROCESSING_TIMEOUT: int = int(os.getenv("PROCESSING_TIMEOUT", "300"))
    
    # Currency Configuration
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "MXN")
    EXCHANGE_RATE_API_KEY: str = os.getenv("EXCHANGE_RATE_API_KEY", "")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_TITLE: str = os.getenv("API_TITLE", "CFDI Invoice Metadata API")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    
    # Ngrok Configuration
    NGROK_AUTH_TOKEN: str = os.getenv("NGROK_AUTH_TOKEN", "")
    NGROK_DOMAIN: str = os.getenv("NGROK_DOMAIN", "")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # Performance Configuration
    ENABLE_PROFILING: bool = os.getenv("ENABLE_PROFILING", "False").lower() == "true"
    MEMORY_LIMIT_MB: int = int(os.getenv("MEMORY_LIMIT_MB", "512"))
    
    # Security Configuration
    ENCRYPT_LOGS: bool = os.getenv("ENCRYPT_LOGS", "False").lower() == "true"
    SENSITIVE_FIELDS: list = ["digital_stamp", "certificate", "sat_seal"]
    
    def __init__(self):
        """Initialize settings and create necessary directories."""
        self._create_directories()
        self._validate_required_settings()
    
    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.INBOX_PATH,
            self.PROCESSED_PATH,
            self.FAILED_PATH,
            self.LOGS_PATH,
            os.path.dirname(self.DATABASE_URL.replace("sqlite:///", ""))
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _validate_required_settings(self) -> None:
        """Validate required settings are present."""
        required_settings = {
            "GEMINI_API_KEY": self.GEMINI_API_KEY,
        }
        
        missing_settings = [
            key for key, value in required_settings.items() 
            if not value
        ]
        
        if missing_settings:
            raise ValueError(f"Missing required settings: {', '.join(missing_settings)}")
    
    def get_database_url(self) -> str:
        """Get database URL with environment-specific handling."""
        if self.ENVIRONMENT == "test":
            return "sqlite:///:memory:"
        return self.DATABASE_URL
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "prod"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "dev"
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as dictionary (excluding sensitive data)."""
        settings_dict = {}
        for attr in dir(self):
            if not attr.startswith('_') and not callable(getattr(self, attr)):
                value = getattr(self, attr)
                # Hide sensitive data
                if 'key' in attr.lower() or 'password' in attr.lower():
                    value = "*" * len(str(value)) if value else ""
                settings_dict[attr] = value
        return settings_dict


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment specific settings."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    DATABASE_ECHO = True


class TestSettings(Settings):
    """Test environment specific settings."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    BATCH_SIZE = 2
    DATABASE_URL = "sqlite:///:memory:"
    GEMINI_TIMEOUT = 10


class ProductionSettings(Settings):
    """Production environment specific settings."""
    DEBUG = False
    LOG_LEVEL = "INFO"
    DATABASE_ECHO = False
    ENCRYPT_LOGS = True
    ENABLE_PROFILING = False


def get_settings() -> Settings:
    """Get settings based on environment."""
    environment = os.getenv("ENVIRONMENT", "dev").lower()
    
    if environment == "test":
        return TestSettings()
    elif environment == "prod":
        return ProductionSettings()
    else:
        return DevelopmentSettings() 