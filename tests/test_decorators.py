import logging
import threading
from unittest.mock import MagicMock, patch

import pytest

from utils.decorators import (log_and_ignore_error, log_and_raise_error,
                              log_and_return_default, log_execution_time,
                              retry_on_failure, trace_class, trace_method, _logged_exceptions)

# Mock logger for testing
mock_logger = MagicMock()

@pytest.fixture(autouse=True)
def reset_mock_logger():
    """Reset the mock logger and clear logged exceptions before each test."""
    mock_logger.reset_mock()
    _logged_exceptions.clear()

# ------------------------------
# Helper Functions
# ------------------------------

def run_in_threads(target, thread_count=5):
    """Run a target function in multiple threads."""
    threads = [threading.Thread(target=target) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

# ------------------------------
# Tests for Error Handling Decorators
# ------------------------------

class TestLogAndRaiseError:
    def test_basic(self):
        @log_and_raise_error("Custom error message", logger=mock_logger, exception_class=ValueError)
        def faulty_function():
            raise RuntimeError("Original error")

        with pytest.raises(ValueError, match="Custom error message"):
            faulty_function()
        mock_logger.error.assert_called_once()

    def test_thread_safe(self):
        @log_and_raise_error("Custom error message", logger=mock_logger, exception_class=ValueError)
        def faulty_function():
            raise RuntimeError("Original error")

        def thread_target():
            with pytest.raises(ValueError, match="Custom error message"):
                faulty_function()

        run_in_threads(thread_target)
        assert mock_logger.error.call_count == 1  # Ensure the error is logged exactly once

class TestLogAndIgnoreError:
    def test_basic(self):
        @log_and_ignore_error("Ignoring error", logger=mock_logger)
        def faulty_function():
            raise RuntimeError("Original error")

        assert faulty_function() is None
        mock_logger.error.assert_called_once()

    def test_thread_safe(self):
        @log_and_ignore_error("Ignoring error", logger=mock_logger)
        def faulty_function():
            raise RuntimeError("Original error")

        run_in_threads(lambda: faulty_function() is None)
        assert mock_logger.error.call_count == 1

class TestLogAndReturnDefault:
    def test_basic(self):
        @log_and_return_default(default_value="default", message="Returning default", logger=mock_logger)
        def faulty_function():
            raise RuntimeError("Original error")

        assert faulty_function() == "default"
        mock_logger.error.assert_called_once()

    def test_thread_safe(self):
        @log_and_return_default(default_value="default", message="Returning default", logger=mock_logger)
        def faulty_function():
            raise RuntimeError("Original error")

        def thread_target():
            result = faulty_function()
            assert result == "default"

        run_in_threads(thread_target)
        assert mock_logger.error.call_count == 1

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
    mock_logger.log.assert_any_call(logging.DEBUG, "Starting %s with args: %s, kwargs: %s", "sample_function", (3, 4), {})
    mock_logger.log.assert_any_call(logging.DEBUG, "Finished %s in %.4f seconds", "sample_function", 1.0)

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
    mock_logger.log.assert_any_call(logging.DEBUG, "Retry attempt %d for function %s", 1, "sample_function")

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
# Revamped Tests for Tracing Decorators
# ------------------------------

def test_trace_method():
    @trace_method(logger=mock_logger)
    def sample_method(x, y):
        return x + y

    # Call the method and verify output
    assert sample_method(3, 4) == 7

    # Collect debug messages logged during the call
    msgs = [call[0][0] for call in mock_logger.debug.call_args_list]

    # Verify that the triggered and finished log messages contain the expected substrings
    assert any("sample_method has triggered." in msg for msg in msgs), "Triggered message missing in trace_method logs"
    assert any("sample_method has finished in" in msg for msg in msgs), "Finished message missing in trace_method logs"

def test_trace_class():
    @trace_class(logger=mock_logger)
    class SampleClass:
        def method_one(self, x):
            return x * 2

        def method_two(self, y):
            return y + 3

    instance = SampleClass()
    # Validate method outputs
    assert instance.method_one(5) == 10
    assert instance.method_two(7) == 10

    # Gather all debug messages
    msgs = [call[0][0] for call in mock_logger.debug.call_args_list]

    # Expected substrings for the log messages
    trigger_one = "SampleClass.method_one has triggered."
    trigger_two = "SampleClass.method_two has triggered."
    finish_one = "SampleClass.method_one has finished in"
    finish_two = "SampleClass.method_two has finished in"

    # Verify that the expected substrings exist in the collected log messages
    assert any(trigger_one in msg for msg in msgs), "Triggered message for method_one missing in trace_class logs"
    assert any(trigger_two in msg for msg in msgs), "Triggered message for method_two missing in trace_class logs"
    assert any(finish_one in msg for msg in msgs), "Finished message for method_one missing in trace_class logs"
    assert any(finish_two in msg for msg in msgs), "Finished message for method_two missing in trace_class logs"
