#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging Configuration for CFDI Processing System v4

Enhanced logging setup with:
- Environment-specific configurations
- File rotation and size limits
- Structured logging with context
- Performance monitoring
- Security considerations for sensitive data

Follows v4 Enhanced Cursor Rules:
- Log all errors with context (filename, line number, operation, component)
- Provide actionable error messages for debugging
- Log security events (API key usage, file access)
- Encrypt sensitive data in logs when necessary
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from config.settings import get_settings


class CFDIFormatter(logging.Formatter):
    """
    Custom formatter for CFDI processing with enhanced context
    """
    
    def __init__(self, include_sensitive: bool = False):
        """
        Initialize formatter.
        
        Args:
            include_sensitive: Whether to include sensitive data in logs
        """
        self.include_sensitive = include_sensitive
        super().__init__()
    
    def format(self, record):
        """Format log record with enhanced context."""
        # Base format
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Add context if available
        context_parts = []
        
        if hasattr(record, 'component'):
            context_parts.append(f"[{record.component}]")
        
        if hasattr(record, 'operation'):
            context_parts.append(f"({record.operation})")
        
        if hasattr(record, 'filename'):
            context_parts.append(f"File: {record.filename}")
        
        if hasattr(record, 'invoice_uuid'):
            context_parts.append(f"UUID: {record.invoice_uuid}")
        
        if hasattr(record, 'processing_time'):
            context_parts.append(f"Time: {record.processing_time:.2f}s")
        
        # Add context to message
        if context_parts:
            context_str = " ".join(context_parts)
            record.msg = f"{context_str} - {record.msg}"
        
        # Use base formatter
        formatter = logging.Formatter(fmt)
        formatted = formatter.format(record)
        
        # Mask sensitive data if needed
        if not self.include_sensitive:
            formatted = self._mask_sensitive_data(formatted)
        
        return formatted
    
    def _mask_sensitive_data(self, message: str) -> str:
        """Mask sensitive data in log messages."""
        import re
        
        # Mask API keys
        message = re.sub(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([A-Za-z0-9_-]{20,})', 
                        r'\1***MASKED***', message, flags=re.IGNORECASE)
        
        # Mask RFC (Mexican tax ID) - keep first 3 and last 3 chars
        message = re.sub(r'\b([A-Z]{3,4})\d{6}([A-Z0-9]{3})\b', 
                        r'\1******\2', message)
        
        # Mask digital stamps (keep first and last 10 chars)
        message = re.sub(r'(digital[_-]?stamp["\']?\s*[:=]\s*["\']?)([A-Za-z0-9+/]{50,})', 
                        r'\1\2[:10]***MASKED***\2[-10:]', message, flags=re.IGNORECASE)
        
        return message


class LoggerAdapter(logging.LoggerAdapter):
    """
    Enhanced logger adapter with processing context
    """
    
    def process(self, msg, kwargs):
        """Add context to log messages."""
        # Add extra context from adapter
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs


def setup_logging(settings: Optional[Any] = None) -> None:
    """
    Setup logging configuration based on environment.
    
    Args:
        settings: Settings object, if None will load from get_settings()
    """
    if settings is None:
        settings = get_settings()
    
    # Create logs directory
    Path(settings.LOGS_PATH).mkdir(parents=True, exist_ok=True)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root log level
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Create formatters
    console_formatter = CFDIFormatter(include_sensitive=settings.is_development())
    file_formatter = CFDIFormatter(include_sensitive=False)  # Never log sensitive to files
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.path.join(settings.LOGS_PATH, 'cfdi_processing.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)  # File always at INFO or above
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler (ERROR and CRITICAL only)
    error_log_file = os.path.join(settings.LOGS_PATH, 'cfdi_errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=settings.LOG_MAX_BYTES // 2,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Performance log handler (if profiling enabled)
    if settings.ENABLE_PROFILING:
        perf_log_file = os.path.join(settings.LOGS_PATH, 'cfdi_performance.log')
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=settings.LOG_MAX_BYTES // 4,
            backupCount=3,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        
        # Special formatter for performance logs
        perf_formatter = logging.Formatter(
            '%(asctime)s - PERF - %(component)s - %(operation)s - %(processing_time).3fs - %(message)s'
        )
        perf_handler.setFormatter(perf_formatter)
        
        # Create performance logger
        perf_logger = logging.getLogger('cfdi.performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False
    
    # Set specific logger levels
    _configure_logger_levels(settings)
    
    # Log setup completion
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Log directory: {settings.LOGS_PATH}")


def _configure_logger_levels(settings) -> None:
    """Configure specific logger levels."""
    # Third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    
    # SQLAlchemy
    if settings.DATABASE_ECHO:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    else:
        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    # Our loggers
    logging.getLogger('src.processing').setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    logging.getLogger('src.data').setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    logging.getLogger('config').setLevel(logging.INFO)


def get_logger(name: str, component: str = None, **context) -> LoggerAdapter:
    """
    Get enhanced logger with processing context.
    
    Args:
        name: Logger name
        component: Component name for context
        **context: Additional context fields
        
    Returns:
        Enhanced logger adapter
    """
    logger = logging.getLogger(name)
    
    # Build context
    extra = {'component': component or name.split('.')[-1]}
    extra.update(context)
    
    return LoggerAdapter(logger, extra)


def log_performance(component: str, operation: str, processing_time: float, **kwargs) -> None:
    """
    Log performance metrics.
    
    Args:
        component: Component name
        operation: Operation name
        processing_time: Processing time in seconds
        **kwargs: Additional metrics
    """
    if get_settings().ENABLE_PROFILING:
        perf_logger = logging.getLogger('cfdi.performance')
        
        message_parts = []
        for key, value in kwargs.items():
            message_parts.append(f"{key}={value}")
        
        message = " | ".join(message_parts) if message_parts else "Performance metric"
        
        perf_logger.info(
            message,
            extra={
                'component': component,
                'operation': operation,
                'processing_time': processing_time
            }
        )


def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        details: Event details
    """
    security_logger = logging.getLogger('cfdi.security')
    
    # Mask sensitive data in details
    safe_details = {}
    for key, value in details.items():
        if any(sensitive in key.lower() for sensitive in ['key', 'password', 'token', 'secret']):
            safe_details[key] = '***MASKED***'
        else:
            safe_details[key] = value
    
    security_logger.warning(
        f"Security Event: {event_type}",
        extra={
            'component': 'security',
            'operation': event_type,
            'event_details': safe_details
        }
    )


def log_api_call(api_name: str, endpoint: str, response_time: float, status_code: int, **kwargs) -> None:
    """
    Log API calls with performance metrics.
    
    Args:
        api_name: Name of the API
        endpoint: API endpoint
        response_time: Response time in seconds
        status_code: HTTP status code
        **kwargs: Additional call details
    """
    api_logger = logging.getLogger('cfdi.api')
    
    level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
    
    api_logger.log(
        level,
        f"{api_name} API call: {endpoint} - {status_code} in {response_time:.3f}s",
        extra={
            'component': 'api_client',
            'operation': 'api_call',
            'api_name': api_name,
            'endpoint': endpoint,
            'processing_time': response_time,
            'status_code': status_code,
            **kwargs
        }
    )


def log_database_operation(operation: str, table: str, processing_time: float, record_count: int = None, **kwargs) -> None:
    """
    Log database operations with performance metrics.
    
    Args:
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        processing_time: Operation time in seconds
        record_count: Number of records affected
        **kwargs: Additional operation details
    """
    db_logger = logging.getLogger('cfdi.database')
    
    message = f"{operation} on {table} in {processing_time:.3f}s"
    if record_count is not None:
        message += f" ({record_count} records)"
    
    db_logger.info(
        message,
        extra={
            'component': 'database',
            'operation': operation.lower(),
            'table': table,
            'processing_time': processing_time,
            'record_count': record_count,
            **kwargs
        }
    )


# Convenience function for backwards compatibility
def configure_logging(settings: Optional[Any] = None) -> None:
    """Alias for setup_logging."""
    setup_logging(settings) 