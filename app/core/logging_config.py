"""
Structured logging configuration
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from app.core.config import settings


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Setup structured logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        log_format: Optional custom log format
    """
    if log_format is None:
        log_format = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers to avoid duplicates/conflicts
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Always add stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(stdout_handler)
    
    # Add file handler if log_file is provided
    if log_file:
        try:
            # Ensure log directory exists (relative to project root)
            # This file is at app/core/logging_config.py, so project root is 2 levels up
            project_root = Path(__file__).parent.parent.parent
            log_path = project_root / log_file
            
            if os.getenv("RENDER") is None:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(str(log_path))
                file_handler.setLevel(getattr(logging, log_level.upper()))
                file_handler.setFormatter(logging.Formatter(log_format))
                root_logger.addHandler(file_handler)
                print(f"File logging configured to: {log_path}")
            else:
                print("Running on Render, skipping file logging. Logging to stdout only.")
        except Exception as e:
            print(f"Failed to setup file logging: {e}. Falling back to stdout.")
    
    # Set log levels for specific libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Setup logging on import
setup_logging(
    log_level="DEBUG" if settings.DEBUG else "INFO",
    log_file="logs/app.log"
)

# Create main application logger
logger = get_logger(__name__)

