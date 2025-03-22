"""
Module for decorators.

This module provides decorators to enhance error handling and logging capabilities.
"""

import functools
import logging
from typing import Type, Callable, Any
import time

def log_and_raise_error(logger: logging.Logger, exception_class: Type[Exception], message: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator factory that wraps a function call in a try-except block, logs the error,
    and raises a specified exception with a custom message when an unexpected error occurs.

    This decorator catches any Exception raised within the decorated function, logs it using
    lazy formatting with the provided logger, and then re-raises the error as an instance of 
    the provided exception class while preserving the original traceback context.

    Parameters:
        logger (logging.Logger): Logger instance used for logging errors.
        exception_class (Type[Exception]): Exception class to be raised on error.
        message (str): Custom error message to log and associate with the raised exception.

    Returns:
        Callable: A decorator that can be applied to any function.

    Example:
        @log_and_raise_error(my_logger, ValueError, "An error occurred")
        def my_function():
            # ...function implementation...
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error("%s: %s", message, e)
                raise exception_class(message) from e
        return wrapper
    return decorator

def log_execution(logger: logging.Logger, log_level: int = logging.DEBUG) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator that logs a function's execution start, parameters, and duration.

    The decorator logs the function name along with its positional and keyword arguments 
    at the beginning of execution, then logs the completion and execution time using the 
    specified log level (default is DEBUG).

    Parameters:
        logger (logging.Logger): Logger instance used for logging.
        log_level (int): Log level for messages; defaults to logging.DEBUG.

    Returns:
        Callable: A decorator that can be applied to any function to log its execution details.

    Example:
        >>> import logging
        >>> logging.basicConfig(level=logging.DEBUG)
        >>> logger = logging.getLogger("example")
        >>>
        >>> @log_execution(logger)
        ... def add(a, b):
        ...     return a + b
        >>>
        >>> result = add(3, 4)
        DEBUG:example:Starting add with args: (3, 4), kwargs: {}
        DEBUG:example:Finished add in 0.0001 seconds
        >>> print(result)
        7
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
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

def retry_on_failure(logger: logging.Logger, retries: int = 3, delay: int = 1000, log_level: int = logging.DEBUG) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator factory that retries a function call when it fails. It catches exceptions during each call,
    logs the exception and retry attempt, and retries the function after a specified delay.
    
    Parameters:
        logger (logging.Logger): Logger instance for logging retry attempts and errors.
        retries (int): Number of retry attempts, default is 3.
        delay (int): Delay between retries in milliseconds, default is 1000 ms.
        log_level (int): Log level for logging retry messages, default is logging.DEBUG.
        
    Returns:
        Callable: A decorator that can be applied to any function to add retry logic.
    
    Example:
        @retry_on_failure(logger, retries=5, delay=500)
        def unstable_function():
            # ...function logic that may raise an exception...
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
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

