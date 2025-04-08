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


# Add helper to check for dunder functions
def _is_dunder(func: Callable[..., Any]) -> bool:
    return func.__name__.startswith("__") and func.__name__.endswith("__")

# Thread-local storage for tracking logged exceptions
_logged_exceptions = threading.local()

def _initialize_thread_local_storage():
    """Initialize thread-local storage for logged exceptions."""
    if not hasattr(_logged_exceptions, "ids"):
        _logged_exceptions.ids = set()

def _reset_thread_local_storage():
    """Reset thread-local storage for testing purposes."""
    if hasattr(_logged_exceptions, "ids"):
        _logged_exceptions.ids.clear()

# ------------------------------
# Error Handling Decorators
# ------------------------------

def log_and_raise_error(
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR),
    exception_class: Type[Exception] = Exception
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator factory that wraps a function call in a try-except block, logs the error,
    and raises a specified exception with a custom message.

    Parameters:
        message (str): Custom message to log and pass to the raised exception.
            Defaults to "An unexpected error occurred."
        logger (logging.Logger): Logger instance for logging errors.
            Defaults to a logger for the current module at ERROR level.
        exception_class (Type[Exception]): Exception type to raise on error.
            Defaults to Exception.

    Returns:
        Callable: A decorator wrapping the target function.

    Note:
        If the target function is a dunder (e.g., __str__), the decorator bypasses logging
        and calls the original function.

    Example:
        @log_and_raise_error("Failed to process data")
        def process_data(data):
            # Process data that might raise an exception.
            pass

        # For a dunder method, logging is skipped:
        class MyClass:
            @log_and_raise_error("Should not log dunder")
            def __repr__(self):
                return "MyClass()"
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _initialize_thread_local_storage()
            if _is_dunder(func):
                return func(*args, **kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not hasattr(_logged_exceptions, "ids"):
                    _logged_exceptions.ids = set()
                if id(e) not in _logged_exceptions.ids:
                    logger.error(
                        "%s: [%s] %s occurred in %s with args: %s, kwargs: %s",
                        message,
                        type(e).__name__,
                        e,
                        func.__name__,
                        args,
                        kwargs,
                    )
                    _logged_exceptions.ids.add(id(e))
                raise exception_class(message) from e
        return wrapper
    return decorator

def log_and_ignore_error(
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR)
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator factory that wraps a function call in a try-except block, logs the error,
    and ignores it (i.e., does not re-raise the exception).

    Parameters:
        message (str): Custom message to log on error.
            Defaults to "An unexpected error occurred."
        logger (logging.Logger): Logger instance for logging errors.
            Defaults to a logger for the current module at ERROR level.

    Returns:
        Callable: A decorator wrapping the target function.

    Note:
        Dunder functions bypass logging and exception handling.
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _initialize_thread_local_storage()
            if _is_dunder(func):
                return func(*args, **kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not hasattr(_logged_exceptions, "ids"):
                    _logged_exceptions.ids = set()
                if id(e) not in _logged_exceptions.ids:
                    logger.error(
                        "%s: [%s] %s occurred in %s with args: %s, kwargs: %s",
                        message,
                        type(e).__name__,
                        e,
                        func.__name__,
                        args,
                        kwargs,
                    )
                    _logged_exceptions.ids.add(id(e))
                return None
        return wrapper
    return decorator

def log_and_return_default(
    default_value: Any,
    message: str = "An unexpected error occurred.",
    logger: logging.Logger = LoggerFactory.get_logger(__name__, handler_level=logging.ERROR)
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator factory that wraps a function call in a try-except block, logs the error,
    and returns a default value instead of raising an exception.

    Parameters:
        default_value: Value to return if the function call fails.
        message (str): Custom message to log on error.
            Defaults to "An unexpected error occurred."
        logger (logging.Logger): Logger instance for logging errors.
            Defaults to a logger for the current module at ERROR level.

    Returns:
        Callable: A decorator wrapping the target function.

    Note:
        Dunder functions execute without logging or error interception.

    Example:
        @log_and_return_default(default_value=[], message="Failed to fetch items")
        def get_feed_items(url):
            # Code that might raise an exception.
            pass

        # In a dunder method:
        class MyClass:
            @log_and_return_default(default_value="Default", message="Not for dunder")
            def __str__(self):
                return "MyClass"
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _initialize_thread_local_storage()
            if _is_dunder(func):
                return func(*args, **kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not hasattr(_logged_exceptions, "ids"):
                    _logged_exceptions.ids = set()
                if id(e) not in _logged_exceptions.ids:
                    logger.error(
                        "%s: [%s] %s occurred in %s with args: %s, kwargs: %s",
                        message,
                        type(e).__name__,
                        e,
                        func.__name__,
                        args,
                        kwargs,
                    )
                    _logged_exceptions.ids.add(id(e))
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
    """
    Decorator for tracing the execution of a single method. Logs when the method is triggered
    and when it completes, including its execution duration.

    Parameters:
        logger (logging.Logger): Logger instance for tracing.
            Defaults to a logger for the current module at DEBUG level.

    Returns:
        Callable: A decorator that wraps the method with tracing functionality.

    Note:
        Dunder methods bypass tracing and execute normally.

    Example:
        class MyClass:
            @trace_method()
            def compute(self, x, y):
                return x + y

            @trace_method()
            def __str__(self):
                # This dunder method will not be traced.
                return "MyClass"
    """
    def decorator(func: Callable[..., Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _is_dunder(func):
                return func(*args, **kwargs)
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
    Class decorator that applies the trace_method decorator to all non-dunder methods
    of the class. This enables execution tracing for each method.

    Parameters:
        cls (Any): The class whose methods are to be traced.

    Returns:
        Any: The modified class with tracing applied to its non-dunder methods.

    Example:
        @trace_class
        class MyClass:
            def method_one(self):
                pass

            def method_two(self):
                pass

            def __repr__(self):
                # Dunder methods are not traced.
                return "MyClass"

        # When method_one or method_two is called, execution tracing is enabled.
    """
    for attr_name, attr in cls.__dict__.items():
        if callable(attr) and not attr_name.startswith("__"):
            setattr(cls, attr_name, trace_method()(attr))
    return cls

