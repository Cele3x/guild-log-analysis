"""
Logging configuration module for Guild Log Analysis.

This module sets up logging to both console and file with proper formatting.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from .settings import Settings


# Track if logging has been configured to avoid duplicate setup
_logging_configured = False


def setup_logging(settings: Optional[Settings] = None) -> None:
    """
    Configure logging for the application.
    
    Sets up logging to write to both console and file with appropriate formatting.
    Only configures logging once per application run.
    
    :param settings: Settings instance (will create new one if not provided)
    """
    global _logging_configured
    
    # Skip if already configured
    if _logging_configured:
        return
    
    if settings is None:
        settings = Settings()
    
    # Create log directory if it doesn't exist
    log_file_path = settings.log_file
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(settings.log_format)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Mark as configured
    _logging_configured = True
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {settings.log_level}, File: {log_file_path}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    :param name: Logger name (typically __name__)
    :returns: Configured logger instance
    """
    return logging.getLogger(name)