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
4. Tracing Decorators:
   - trace_method: Traces method execution.
   - trace_class: Applies trace_method to all non-dunder methods of a class.

Note:
    For all decorators, if the decorated function is a dunder (its name starts and ends with '__'),
    the original function is executed without any added logging, error handling, retry, or tracing.
"""

import functools
import logging
import time
from typing import Any, Callable, Type
import threading

from utils.logger import LoggerFactory

# Thread-safe set for tracking logged exceptions
class LogOnceTracker:
    """Thread-safe tracker for logging messages only once."""
    def __init__(self):
        self._lock = threading.Lock()
        self._logged_exceptions = set()

    def log_once(self, logger: logging.Logger, level: int, message: str, *args: Any) -> None:
        """Log a message only once across threads using the specified logging level."""
        with self._lock:
            if message not in self._logged_exceptions:
                logger.log(level, message, *args)
                self._logged_exceptions.add(message)

# Create a shared instance of LogOnceTracker
_log_once_tracker = LogOnceTracker()

def _log_once(logger: logging.Logger, level: int, message: str, *args: Any) -> None:
    """Wrapper around LogOnceTracker to maintain the same interface."""
    _log_once_tracker.log_once(logger, level, message, *args)

def _is_dunder(func: Callable[..., Any]) -> bool:
    """Check if a function is a dunder method."""
    return func.__name__.startswith("__") and func.__name__.endswith("__")

# ------------------------------
# Error Handling Decorators
# ------------------------------

def log_and_raise_error(
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR),
    exception_class: Type[Exception] = Exception,
    log_level: int = logging.ERROR  # Added log_level parameter
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Log an error and raise a specified exception."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _is_dunder(func):
                return func(*args, **kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Ensure consistent error message
                error_message = f"{message}: [{type(e).__name__}] {e} in {func.__name__} with args: {args}, kwargs: {kwargs}"
                _log_once(logger, log_level, error_message)  # Use log_level
                _log_once(logger, log_level, error_message)  # Use log_level
                raise exception_class(message) from e
        return wrapper
    return decorator

def log_and_ignore_error(
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR),
    log_level: int = logging.ERROR  # Added log_level parameter
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Log an error and ignore it."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _is_dunder(func):
                return func(*args, **kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_message = f"{message}: [{type(e).__name__}] {e} in {func.__name__} with args: {args}, kwargs: {kwargs}"
                _log_once(logger, log_level, error_message)  # Use log_level
                _log_once(logger, log_level, error_message)  # Use log_level
                return None
        return wrapper
    return decorator

def log_and_return_default(
    default_value: Any,
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR),
    log_level: int = logging.ERROR  # Added log_level parameter
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Log an error and return a default value."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _is_dunder(func):
                return func(*args, **kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_message = f"{message}: [{type(e).__name__}] {e} in {func.__name__} with args: {args}, kwargs: {kwargs}"
                _log_once(logger, log_level, error_message)  # Use log_level
                _log_once(logger, log_level, error_message)  # Use log_level
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
    Decorator that logs the start, parameters, and duration of a function's execution.

    Parameters:
        logger (logging.Logger): Logger instance for logging execution details.
            Defaults to a logger for the current module at DEBUG level.
        log_level (int): Logging level for execution logs.
            Defaults to logging.DEBUG.

    Returns:
        Callable: A decorator wrapping the target function.

    Note:
        If the target function is a dunder, execution is unmodified.

    Example:
        @log_execution_time
        def compute(x, y):
            return x + y

        # In a class, dunder bypass:
        class MyClass:
            @log_execution_time
            def __init__(self):
                self.value = 0
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _is_dunder(func):
                return func(*args, **kwargs)
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
    Decorator factory that retries a function call upon failure. It catches exceptions,
    logs each retry attempt, and reattempts after a specified delay until the retry limit is reached.

    Parameters:
        logger (logging.Logger): Logger instance for logging retry attempts and errors.
            Defaults to a logger for the current module at DEBUG level.
        retries (int): Maximum number of retry attempts.
            Defaults to 3.
        delay (int): Delay in milliseconds between retries.
            Defaults to 1000 (1 second).
        log_level (int): Logging level for retry messages.
            Defaults to logging.DEBUG.

    Returns:
        Callable: A decorator wrapping the target function.

    Note:
        Dunder functions are not subject to retry logic or logging.

    Example:
        @retry_on_failure(retries=5, delay=2000)
        def unstable_function():
            # Function that may intermittently fail.
            pass

        # Dunder method example:
        class MyClass:
            @retry_on_failure
            def __str__(self):
                return "MyClass"
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _is_dunder(func):
                return func(*args, **kwargs)
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
    """Trace the execution of a method."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _is_dunder(func):
                return func(*args, **kwargs)
            method_name = func.__name__
            logger.debug(f"{method_name} has triggered.")
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            logger.debug(f"{method_name} has finished in {duration:.4f} seconds.")
            return result
        return wrapper
    return decorator

def trace_class(logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.DEBUG)) -> Callable[[Any], Any]:
    """Apply trace_method to all non-dunder methods of a class."""
    def decorator(cls: Any) -> Any:
        for attr_name, attr in cls.__dict__.items():
            if callable(attr) and not attr_name.startswith("__"):
                # Wrap the method with trace_method, preserving existing decorators
                original_method = attr
                @functools.wraps(original_method)
                def wrapped_method(*args, **kwargs):
                    logger.debug(f"Entering {cls.__name__}.{attr_name} with args: {args}, kwargs: {kwargs}")
                    result = original_method(*args, **kwargs)
                    logger.debug(f"Exiting {cls.__name__}.{attr_name} with result: {result}")
                    return result
                setattr(cls, attr_name, wrapped_method)
        return cls
    return decorator


