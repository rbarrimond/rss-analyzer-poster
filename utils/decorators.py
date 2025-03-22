"""
Module for decorators.

This module provides decorators to enhance error handling, logging, and retry capabilities.
Each decorator includes detailed parameter descriptions and usage examples.
"""

import functools
import logging
from typing import Type, Callable, Any
import time
from utils.logger import LoggerFactory

def log_and_raise_error(
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR),
    exception_class: Type[Exception] = Exception
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator factory that wraps a function call in a try-except block, logs the error,
    and raises a specified exception with a custom message when an unexpected error occurs.
    
    Parameters:
        message (str): Custom message to log and pass to the raised exception.
            Defaults to "An unexpected error occurred."
        logger (logging.Logger): Logger instance to use for logging errors.
            Defaults to a logger created for the current module at ERROR level.
        exception_class (Type[Exception]): Exception type to be raised.
            Defaults to Exception.
    
    Returns:
        Callable: A decorator that wraps the target function.
    
    Example:
        @log_and_raise_error("An error occurred in process_data.")
        def process_data(data):
            # Process the data and possibly raise an exception.
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error("%s: %s", message, e)
                raise exception_class(message) from e
        return wrapper
    return decorator

def log_execution_time(
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.DEBUG),
    log_level: int = logging.DEBUG
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator that logs a function's execution start, parameters, and duration.
    
    Parameters:
        logger (logging.Logger): Logger instance to use for logging execution details.
            Defaults to a logger created for the current module at DEBUG level.
        log_level (int): Logging level for the execution logs.
            Defaults to logging.DEBUG.
    
    Returns:
        Callable: A decorator that wraps the target function.
    
    Example:
        @log_execution_time
        def compute(x, y):
            return x + y
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            logger.log(log_level, "Starting %s with args: %s, kwargs: %s", func.__name__, args, kwargs)
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            logger.log(log_level, "Finished %s in %.4f seconds", func.__name__, duration)
            return result
        return wrapper
    return decorator

def retry_on_failure(
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.DEBUG),
    retries: int = 3,
    delay: int = 1000,
    log_level: int = logging.DEBUG
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator factory that retries a function call when it fails. It catches exceptions during each call,
    logs the exception and retry attempt, and retries the function after a specified delay.
    
    Parameters:
        logger (logging.Logger): Logger instance to use for logging retry attempts and errors.
            Defaults to a logger created for the current module at DEBUG level.
        retries (int): Number of retry attempts before giving up.
            Defaults to 3.
        delay (int): Delay in milliseconds between retry attempts.
            Defaults to 1000 (1 second).
        log_level (int): Logging level for retry messages.
            Defaults to logging.DEBUG.
    
    Returns:
        Callable: A decorator that wraps the target function.
    
    Example:
        @retry_on_failure(retries=5, delay=2000)
        def unstable_function():
            # Code that might fail intermittently.
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while attempt <= retries:
                try:
                    if attempt > 0:
                        logger.log(log_level, "Retry attempt %d for function %s", attempt, func.__name__)
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error("Exception on attempt %d for function %s: %s", attempt, func.__name__, e)
                    attempt += 1
                    if attempt > retries:
                        raise
                    time.sleep(delay / 1000.0)
        return wrapper
    return decorator

