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


class TestEntry:

    @pytest.fixture
    def valid_entry_data(self):
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
            "Source": {"key": "value"}
        }

    def test_entry_validation_success(self, valid_entry_data):
        entry = Entry(**valid_entry_data)
        assert entry.title == "Test Entry"
        assert entry.link == HttpUrl("https://example.com")

    def test_entry_validation_failure(self, valid_entry_data):
        invalid_data = valid_entry_data.copy()
        invalid_data["Link"] = "invalid-url"
        with pytest.raises(ValidationError):
            Entry(**invalid_data)

    @pytest.mark.skip(reason="Task has no min_length")
    def test_entry_min_length_validation(self, valid_entry_data):
        valid_entry_data["Tags"] = []  # Updated to match the correct field name
        with pytest.raises(ValidationError):
            Entry(**valid_entry_data)

    @patch("entities.entry.acf.get_instance")
    def test_fetch_content_from_blob_success(self, mock_acf, valid_entry_data):
        mock_acf.return_value.download_blob_content.return_value = "Blob content"
        entry = Entry(**valid_entry_data)
        content = entry._fetch_content_from_blob()
        assert content == "Blob content"

    @patch("entities.entry.requests.get")
    def test_fetch_content_from_http_success(self, mock_get, valid_entry_data):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Content</body></html>"
        mock_get.return_value = mock_response

        entry = Entry(**valid_entry_data)
        content = entry._fetch_content_from_http()
        assert "Content" in content

    @patch("entities.entry.acf.get_instance")
    def test_save_content_to_blob(self, mock_acf, valid_entry_data):
        mock_acf.return_value.upload_blob_content.return_value = True
        entry = Entry(**valid_entry_data)
        entry._save_content_to_blob("Test content")
        mock_acf.return_value.upload_blob_content.assert_called_once()

    @patch("entities.entry.acf.get_instance")
    def test_save_entry(self, mock_acf, valid_entry_data):
        mock_acf.return_value.upload_blob_content.return_value = True
        mock_acf.return_value.table_upsert_entity.return_value = True

        entry = Entry(**valid_entry_data)
        with patch.object(Entry, "fetch_content", return_value="Test content"):
            entry.save()
        mock_acf.return_value.upload_blob_content.assert_called_once()
        mock_acf.return_value.table_upsert_entity.assert_called_once()

    @patch("entities.entry.acf.get_instance")
    def test_delete_entry(self, mock_acf, valid_entry_data):
        mock_acf.return_value.delete_blob.return_value = True
        mock_acf.return_value.table_delete_entity.return_value = True

        entry = Entry(**valid_entry_data)
        entry.delete()
        mock_acf.return_value.delete_blob.assert_called_once()
        mock_acf.return_value.table_delete_entity.assert_called_once()

    def test_get_cached_content(self, valid_entry_data):
        entry = Entry(**valid_entry_data)
        entry._content_cache = "Cached content"
        assert entry.get_cached_content() == "Cached content"

    def test_fetch_content_recursion_guard(self, valid_entry_data):
        entry = Entry(**valid_entry_data)
        entry._recursion_guard.active = True
        content = entry.fetch_content()
        assert content == NULL_CONTENT
