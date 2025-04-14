"""Test cases for the AIEnrichment class.
This module contains unit tests for the AIEnrichment class, which is responsible for
handling AI-generated enrichment data. The tests cover various scenarios, including
successful and failed operations for fetching, saving, and deleting enrichment data.
"""
from unittest.mock import patch, MagicMock
import io
import numpy as np
import pytest

from entities.entry import AIEnrichment

# pylint: disable=protected-access
# pylint: disable=unused-import
# pylint: disable=C

class TestAIEnrichment:

    @pytest.fixture
    def valid_enrichment_data(self):
        return {
            "PartitionKey": "entry",
            "RowKey": "1a2b3c4d5e6f7g8h",  # Example 16-digit hexadecimal string
            "Summary": "AI-generated summary",
            "GradeLevel": 10.5,
            "Difficulty": 8.0,
            "EngagementScore": 7.5,
            "EngagementCategories": {"Liked", "Shared"}
        }

    @patch("entities.entry.acf.get_instance")
    def test_fetch_embeddings_from_blob_success(self, mock_acf, valid_enrichment_data):
        # Test successful retrieval of embeddings from blob storage
        mock_blob_content = io.BytesIO()
        np.save(mock_blob_content, np.array([1, 2, 3]))
        mock_blob_content.seek(0)
        mock_acf.return_value.download_blob_content.return_value = mock_blob_content.getvalue()

        enrichment = AIEnrichment(**valid_enrichment_data)
        embeddings = enrichment._fetch_embeddings_from_blob()

        assert (embeddings == np.array([1, 2, 3])).all()

    @patch("entities.entry.acf.get_instance")
    def test_save_embeddings_to_blob(self, mock_acf, valid_enrichment_data):
        # Test successful saving of embeddings to blob storage
        mock_acf.return_value.upload_blob_content.return_value = True

        enrichment = AIEnrichment(**valid_enrichment_data)
        embeddings = np.array([1, 2, 3])

        with patch("io.BytesIO", new_callable=MagicMock) as mock_bytes_io:
            enrichment._save_embeddings_to_blob(embeddings)
            mock_acf.return_value.upload_blob_content.assert_called_once()
            mock_bytes_io.assert_called()

    @patch("entities.entry.acf.get_instance")
    def test_save_enrichment(self, mock_acf, valid_enrichment_data):
        # Test successful saving of enrichment data
        mock_acf.return_value.upload_blob_content.return_value = True
        mock_acf.return_value.table_upsert_entity.return_value = True

        enrichment = AIEnrichment(**valid_enrichment_data)
        enrichment.save(save_embeddings=np.array([1, 2, 3]))

        mock_acf.return_value.upload_blob_content.assert_called_once()
        mock_acf.return_value.table_upsert_entity.assert_called_once()

    @patch("entities.entry.acf.get_instance")
    def test_delete_enrichment(self, mock_acf, valid_enrichment_data):
        # Test successful deletion of enrichment data
        mock_acf.return_value.delete_blob.return_value = True
        mock_acf.return_value.table_delete_entity.return_value = True

        enrichment = AIEnrichment(**valid_enrichment_data)
        enrichment.delete()

        mock_acf.return_value.delete_blob.assert_called_once()
        mock_acf.return_value.table_delete_entity.assert_called_once()

    @patch("entities.entry.acf.get_instance")
    @patch("utils.logger.LoggerFactory.get_logger")
    def test_log_and_raise_error_decorator(self, mock_logger, mock_acf, valid_enrichment_data):
        # Test the log_and_raise_error decorator
        mock_acf.return_value.upload_blob_content.side_effect = Exception("Upload failed")
        enrichment = AIEnrichment(**valid_enrichment_data)

        with pytest.raises(Exception, match=r"Failed to persist embeddings"):
            enrichment._save_embeddings_to_blob(np.array([1, 2, 3]))

        mock_logger.return_value.error.assert_called_with(
            "Failed to persist embeddings: [Exception] Upload failed in _save_embeddings_to_blob with args: (), kwargs: {}"
        )

    @patch("entities.entry.acf.get_instance")
    @patch("utils.logger.LoggerFactory.get_logger")
    def test_log_and_return_default_decorator(self, mock_logger, mock_acf, valid_enrichment_data):
        # Test the log_and_return_default decorator
        mock_acf.return_value.download_blob_content.side_effect = Exception("Blob not found")
        enrichment = AIEnrichment(**valid_enrichment_data)

        result = enrichment._fetch_embeddings_from_blob()
        assert result is None

        mock_logger.return_value.error.assert_called_with(
            "Failed to retrieve content blob: [Exception] Blob not found in _fetch_embeddings_from_blob with args: (), kwargs: {}"
        )

    @patch("entities.entry.acf.get_instance")
    @patch("utils.logger.LoggerFactory.get_logger")
    def test_retry_on_failure_decorator(self, mock_logger, mock_acf, valid_enrichment_data):
        # Test the retry_on_failure decorator
        mock_acf.return_value.upload_blob_content.side_effect = Exception("Upload failed")
        enrichment = AIEnrichment(**valid_enrichment_data)

        with pytest.raises(Exception, match=r"Failed to persist embeddings"):
            enrichment._save_embeddings_to_blob(np.array([1, 2, 3]))

        assert mock_logger.return_value.error.call_count == 2  # One for each retry
        mock_logger.return_value.error.assert_any_call(
            "Exception on attempt 0 for function _save_embeddings_to_blob: Upload failed"
        )
        mock_logger.return_value.error.assert_any_call(
            "Exception on attempt 1 for function _save_embeddings_to_blob: Upload failed"
        )
