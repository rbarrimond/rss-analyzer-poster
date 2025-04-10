import os
import sys
from unittest.mock import MagicMock

import pytest

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def mock_azure_clients(monkeypatch):
    """
    Automatically mock AzureClientFactory to prevent real Azure operations during tests.
    """
    mock_acf = MagicMock()
    monkeypatch.setattr("utils.azclients.AzureClientFactory.get_instance", lambda: mock_acf)
    return mock_acf