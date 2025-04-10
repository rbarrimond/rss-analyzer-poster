from unittest.mock import patch

import numpy as np
import pytest

from entities.entry import AIEnrichment


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
        mock_acf.return_value.download_blob_content.return_value = np.array([1, 2, 3]).tobytes()
        enrichment = AIEnrichment(**valid_enrichment_data)
        embeddings = enrichment._fetch_embeddings_from_blob()
        assert (embeddings == np.array([1, 2, 3])).all()

    @patch("entities.entry.acf.get_instance")
    def test_save_embeddings_to_blob(self, mock_acf, valid_enrichment_data):
        mock_acf.return_value.upload_blob_content.return_value = True
        enrichment = AIEnrichment(**valid_enrichment_data)
        enrichment._save_embeddings_to_blob(np.array([1, 2, 3]))
        mock_acf.return_value.upload_blob_content.assert_called_once()

    @patch("entities.entry.acf.get_instance")
    def test_save_enrichment(self, mock_acf, valid_enrichment_data):
        mock_acf.return_value.upload_blob_content.return_value = True
        mock_acf.return_value.table_upsert_entity.return_value = True

        enrichment = AIEnrichment(**valid_enrichment_data)
        enrichment.save(save_embeddings=np.array([1, 2, 3]))
        mock_acf.return_value.upload_blob_content.assert_called_once()
        mock_acf.return_value.table_upsert_entity.assert_called_once()

    @patch("entities.entry.acf.get_instance")
    def test_delete_enrichment(self, mock_acf, valid_enrichment_data):
        mock_acf.return_value.delete_blob.return_value = True
        mock_acf.return_value.table_delete_entity.return_value = True

        enrichment = AIEnrichment(**valid_enrichment_data)
        enrichment.delete()
        mock_acf.return_value.delete_blob.assert_called_once()
        mock_acf.return_value.table_delete_entity.assert_called_once()
