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
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Add file handler if log_file is provided
    if log_file:
        try:
            log_path = Path(log_file)
            # Ensure log directory exists (relative to project root)
            log_dir = log_path.parent
            if not log_dir.is_absolute():
                # If relative path, make it relative to project root
                # This file is at app/core/logging_config.py, so project root is 3 levels up
                project_root = Path(__file__).parent.parent.parent
                log_path = project_root / log_file
                log_dir = log_path.parent
            
            # Only create directory and add handler if OS environment is not Render
            # or if it's explicitly allowed. Render filesystem is mostly read-only.
            if os.getenv("RENDER") is None:
                log_dir.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(str(log_path))
                file_handler.setLevel(getattr(logging, log_level.upper()))
                file_handler.setFormatter(logging.Formatter(log_format))
                logging.getLogger().addHandler(file_handler)
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
    log_file="logs/app.log" if not settings.DEBUG else None
)

# Create main application logger
logger = get_logger(__name__)

