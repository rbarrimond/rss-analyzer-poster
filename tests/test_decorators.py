import logging
from unittest.mock import MagicMock, patch

import pytest

from utils.decorators import (log_and_ignore_error, log_and_raise_error,
                              log_and_return_default, log_execution_time,
                              retry_on_failure, trace_class, trace_method)

# Mock logger for testing
mock_logger = MagicMock()

# ------------------------------
# Tests for Error Handling Decorators
# ------------------------------

def test_log_and_raise_error():
    @log_and_raise_error("Custom error message", logger=mock_logger, exception_class=ValueError)
    def faulty_function():
        raise RuntimeError("Original error")

    with pytest.raises(ValueError, match="Custom error message"):
        faulty_function()
    mock_logger.error.assert_called_once()

def test_log_and_ignore_error():
    @log_and_ignore_error("Ignoring error", logger=mock_logger)
    def faulty_function():
        raise RuntimeError("Original error")

    assert faulty_function() is None  # Should return None and not raise an exception
    mock_logger.error.assert_called_once()

def test_log_and_return_default():
    @log_and_return_default(default_value="default", message="Returning default", logger=mock_logger)
    def faulty_function():
        raise RuntimeError("Original error")

    assert faulty_function() == "default"  # Should return the default value
    mock_logger.error.assert_called_once()

# ------------------------------
# Tests for Performance Decorators
# ------------------------------

@patch("time.perf_counter", side_effect=[1, 2])  # Mock time to simulate 1 second duration
def test_log_execution_time(mock_time):
    @log_execution_time(logger=mock_logger)
    def sample_function(x, y):
        return x + y

    result = sample_function(3, 4)
    assert result == 7
    mock_logger.log.assert_called_with(
        logging.DEBUG, 
        "Finished %s in %.4f seconds", 
        "sample_function", 
        1.0
    )

# ------------------------------
# Tests for Retry Decorators
# ------------------------------

def test_retry_on_failure_success():
    mock_function = MagicMock(side_effect=[RuntimeError("Fail"), "Success"])
    @retry_on_failure(logger=mock_logger, retries=2, delay=0)
    def sample_function():
        return mock_function()

    assert sample_function() == "Success"
    assert mock_function.call_count == 2
    mock_logger.log.assert_called_with(logging.DEBUG, "Retry attempt %d for function %s", 1, "sample_function")

def test_retry_on_failure_exhausted():
    mock_function = MagicMock(side_effect=RuntimeError("Fail"))
    @retry_on_failure(logger=mock_logger, retries=2, delay=0)
    def sample_function():
        return mock_function()

    with pytest.raises(RuntimeError, match="Fail"):
        sample_function()
    assert mock_function.call_count == 3  # Initial attempt + 2 retries
    mock_logger.error.assert_called()

# ------------------------------
# Tests for Tracing Decorators
# ------------------------------

def test_trace_method():
    @trace_method(logger=mock_logger)
    def sample_method(x, y):
        return x + y

    result = sample_method(3, 4)
    assert result == 7
    mock_logger.debug.assert_any_call("sample_method has triggered.")
    mock_logger.debug.assert_any_call("sample_method has finished in")

def test_trace_class():
    @trace_class
    class SampleClass:
        def method_one(self, x):
            return x * 2

        def method_two(self, y):
            return y + 3

    instance = SampleClass()
    assert instance.method_one(5) == 10
    assert instance.method_two(7) == 10
    mock_logger.debug.assert_any_call("SampleClass.method_one has triggered.")
    mock_logger.debug.assert_any_call("SampleClass.method_two has triggered.")

def test_trace_class_no_recursion():
    @trace_class
    class TestClass:
        def method(self, x):
            if x > 0:
                return self.method(x - 1)
            return x

    instance = TestClass()
    assert instance.method(5) == 0  # Ensure recursion terminates correctly

def test_retry_on_failure_no_recursion():
    @retry_on_failure(retries=3, delay=10)
    def recursive_function(x):
        if x > 0:
            return recursive_function(x - 1)
        return x

    assert recursive_function(5) == 0  # Ensure recursion terminates correctly
