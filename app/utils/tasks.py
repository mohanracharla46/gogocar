"""
Background task utilities for async operations
"""
from typing import Callable, Any
from functools import wraps
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

from app.core.logging_config import logger

# Thread pool executor for background tasks
_executor = ThreadPoolExecutor(max_workers=10)


def run_in_background(func: Callable) -> Callable:
    """
    Decorator to run a function in background thread
    
    Usage:
        @run_in_background
        def send_email_task(email, subject, body):
            # Send email
            pass
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            _executor.submit(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error running background task {func.__name__}: {str(e)}")
    return wrapper


def run_async_task(func: Callable) -> Callable:
    """
    Decorator to run an async function in background
    
    Usage:
        @run_async_task
        async def send_email_task(email, subject, body):
            # Send email
            pass
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(func(*args, **kwargs))
            loop.close()
        except Exception as e:
            logger.error(f"Error running async background task {func.__name__}: {str(e)}")
    return wrapper


def schedule_task(func: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Schedule a function to run in background
    
    Args:
        func: Function to run
        *args: Positional arguments
        **kwargs: Keyword arguments
    """
    try:
        _executor.submit(func, *args, **kwargs)
    except Exception as e:
        logger.error(f"Error scheduling task {func.__name__}: {str(e)}")

