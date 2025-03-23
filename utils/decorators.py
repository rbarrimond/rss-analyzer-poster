"""Module for decorators.

This module provides a collection of decorators organized into logical groups:
1. Error Handling Decorators:
   - log_and_raise_error: Logs an error then raises a specified exception.
   - log_and_ignore_error: Logs an error and ignores it.
   - log_and_return_default: Logs an error and returns a default value.
2. Performance Decorators:
   - log_execution_time: Logs function execution start, parameters, and duration.
3. Retry Decorators:
   - retry_on_failure: Retries a function when it fails, with error logging and delay.

These decorators enhance error handling, logging, and retry capabilities.
"""

import functools
import logging
from typing import Type, Callable, Any
import time
from utils.logger import LoggerFactory

# ------------------------------
# Error Handling Decorators
# ------------------------------

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

def log_and_ignore_error(
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR)
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator factory that wraps a function call in a try-except block, logs
    the error, and ignores it (i.e., does not re-raise an exception).

    Parameters:
        message (str): Custom message to log on error.
            Defaults to "An unexpected error occurred."
        logger (logging.Logger): Logger instance to use for logging errors.
            Defaults to a logger created for the current module at ERROR level.

    Returns:
        Callable: A decorator that wraps the target function.

    Example:
        @log_and_ignore_error("An error occurred in process_data.")
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
                # Error is ignored; return None by default.
        return wrapper
    return decorator

def log_and_return_default(
    default_value: Any,
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR)
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator factory that wraps a function call in a try-except block, logs
    the error, and returns a default value instead of raising the exception.

    Parameters:
        default_value: The return value to use when the function call fails.
        message (str): Custom message to log on error.
            Defaults to "An unexpected error occurred."
        logger (logging.Logger): Logger instance to use for logging errors.
            Defaults to a logger created for the current module at ERROR level.

    Returns:
        Callable: A decorator that wraps the target function.

    Example:
        @log_and_return_default(default_value=[])
        def get_feed_items(feed_url):
            # Process the feed and possibly raise an exception.
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error("%s: %s", message, e)
                return default_value
        return wrapper
    return decorator

# ------------------------------
# Performance Decorators
# ------------------------------

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

# ------------------------------
# Retry Decorators
# ------------------------------

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

# ------------------------------
# Tracing Decorators
# ------------------------------

def trace_method(logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.DEBUG)):
    """
    A decorator for tracing a single method's execution.

    This decorator logs when the method is triggered and when it finishes along with its execution time.
    It extracts the class name from the first argument (assumed to be an instance) and logs messages 
    using the provided logger.

    Parameters:
        logger (logging.Logger): Logger instance to log tracing information.
            Defaults to a logger created for the current module at DEBUG level.

    Returns:
        Callable: A decorator that wraps the method with tracing functionality.

    Example:
        class MyClass:
            @trace_method()
            def my_method(self):
                # ...existing code...
                pass

        obj = MyClass()
        obj.my_method()
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            class_name = args[0].__class__.__name__ if args else ''
            method_name = func.__name__
            logger.debug("%s.%s has triggered.", class_name, method_name)
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            logger.debug("%s.%s has finished in %.4f seconds.", class_name, method_name, duration)
            return result
        return wrapper
    return decorator

def trace_class(cls: Any) -> Any:
    """
    A class decorator that applies the trace_method decorator to all non-dunder methods of a class.

    This decorator iterates over the class's attributes and wraps each callable attribute 
    (excluding those whose names start with '__') with the trace_method decorator, enabling
    execution tracing for each method.

    Parameters:
        cls (Any): The class whose methods will be wrapped with trace_method.

    Returns:
        Any: The modified class with tracing enabled on its non-dunder methods.

    Example:
        @trace_class
        class MyClass:
            def method_one(self):
                # ...existing code...
                pass

            def method_two(self):
                # ...existing code...
                pass

        obj = MyClass()
        obj.method_one()
        obj.method_two()
    """
    for attr_name, attr in cls.__dict__.items():
        if callable(attr) and not attr_name.startswith("__"):
            setattr(cls, attr_name, trace_method()(attr))
    return cls

