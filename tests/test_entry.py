"""
Test cases for the Entry class.
This module contains unit tests for the Entry class, which is part of the entities.entry module.
The tests cover various functionalities of the Entry class, including validation, content fetching,
content saving, and entry management.
"""
# pylint: disable=missing-docstring
# pylint: disable=W0212

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import HttpUrl, ValidationError

# Fix import errors by ensuring correct paths
from entities.entry import NULL_CONTENT, Entry  # Ensure 'entities.entry' is the correct module path


@pytest.fixture
def valid_entry_data():
    return {
        "PartitionKey": "entry",
        "Id": "unique-id",
        "FeedKey": "1234567890abcdef",
        "Title": "Test Entry",
        "Link": "https://example.com",
        "Published": datetime(2023, 1, 1),
        "Author": "Author Name",
        "Tags": ["tag1", "tag2"],
        "Summary": "This is a test summary.",
        "Source": {"key": "value"},
        "Content": "This is a test content."  # Ensure Content is a valid string to avoid serialization issues
    }


class TestEntryValidation:

    def test_entry_missing_required_field(self, valid_entry_data):
        invalid_data = valid_entry_data.copy()
        del invalid_data["FeedKey"]  # Remove a truly required field
        with pytest.raises(ValidationError, match="Field required"):
            Entry(**invalid_data)

    def test_entry_invalid_published_date(self, valid_entry_data):
        invalid_data = valid_entry_data.copy()
        invalid_data["Published"] = "not-a-date"
        with pytest.raises(ValidationError, match="Value error, Invalid date format for 'published': not-a-date "):
            Entry(**invalid_data)

    def test_entry_empty_tags(self, valid_entry_data):
        valid_entry_data["Tags"] = []
        entry = Entry(**valid_entry_data)
        assert entry.tags == []

    def test_entry_invalid_url(self, valid_entry_data):
        invalid_data = valid_entry_data.copy()
        invalid_data["Link"] = "ftp://invalid-url"
        with pytest.raises(ValidationError, match="URL scheme should be 'http' or 'https'"):
            Entry(**invalid_data)


class TestEntryContentFetching:

    def test_fetch_content_no_source(self, valid_entry_data):
        valid_entry_data["Source"] = None
        valid_entry_data["Content"] = None  # Ensure Content is None for this test
        entry = Entry(**valid_entry_data)
        content = entry.fetch_content()
        assert content == NULL_CONTENT

    @patch("entities.entry.requests.get")
    def test_fetch_content_http_success(self, mock_get, valid_entry_data):
        valid_entry_data["Content"] = None  # Ensure Content is None to test HTTP fetching
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test Content</body></html>"
        mock_get.return_value = mock_response

        entry = Entry(**valid_entry_data)
        content = entry._fetch_content_from_http()
        assert "Test Content" in content

    @patch("entities.entry.log_execution_time")  # Mocking the decorator
    def test_fetch_content_with_logging(self, mock_decorator, valid_entry_data):
        mock_decorator.return_value = lambda func: func  # Mock decorator to return the original function
        entry = Entry(**valid_entry_data)
        content = entry.fetch_content()
        assert content == NULL_CONTENT  # Assuming default behavior
        mock_decorator.assert_called_once()

    @patch("entities.entry.retry_on_failure")  # Mocking retry decorator
    def test_fetch_content_with_retry(self, mock_retry, valid_entry_data):
        mock_retry.return_value = lambda func: func  # Mock decorator to return the original function
        entry = Entry(**valid_entry_data)
        with patch.object(entry, "_fetch_content_from_http", side_effect=Exception("Retry test")):
            with pytest.raises(Exception, match="Retry test"):
                entry.fetch_content()
        mock_retry.assert_called_once()

    @patch("entities.entry.log_and_return_default")  # Mocking the decorator
    def test_fetch_content_with_default_return(self, mock_decorator, valid_entry_data):
        mock_decorator.return_value = lambda func: func  # Mock decorator to return the original function
        entry = Entry(**valid_entry_data)
        with patch.object(entry, "_fetch_content_from_http", side_effect=Exception("HTTP error")):
            content = entry._fetch_content_from_http()
            assert content is None  # Default value returned by the decorator
        mock_decorator.assert_called_once()


class TestEntryContentSaving:

    @patch("entities.entry.acf.get_instance")
    @patch("entities.entry.log_and_raise_error")  # Mocking the decorator
    def test_save_content_with_error_logging(self, mock_decorator, mock_acf, valid_entry_data):
        mock_decorator.return_value = lambda func: func  # Mock decorator to return the original function
        mock_acf.return_value.upload_blob_content.return_value = True
        entry = Entry(**valid_entry_data)
        entry._save_content_to_blob("Test content")
        mock_acf.return_value.upload_blob_content.assert_called_once()
        mock_decorator.assert_called_once()


class TestEntryDeletion:

    @patch("entities.entry.acf.get_instance")
    @patch("entities.entry.log_and_raise_error")  # Mocking the decorator
    def test_delete_entry_with_error_logging(self, mock_decorator, mock_acf, valid_entry_data):
        mock_decorator.return_value = lambda func: func  # Mock decorator to return the original function
        mock_acf.return_value.delete_blob.return_value = True
        mock_acf.return_value.table_delete_entity.return_value = True

        # Ensure valid_entry_data does not contain MagicMock objects
        valid_entry_data["Content"] = "Test content"  # Replace MagicMock with a valid string

        entry = Entry(**valid_entry_data)
        entry.delete()
        mock_acf.return_value.delete_blob.assert_called_once()
        mock_acf.return_value.table_delete_entity.assert_called_once()
        mock_decorator.assert_called_once()


class TestEntryCache:

    def test_get_cached_content_empty(self, valid_entry_data):
        entry = Entry(**valid_entry_data)
        entry._content_cache = None
        assert entry.get_cached_content() is None
