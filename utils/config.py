"""Module providing the ConfigLoader class for loading configuration from Azure Blob storage."""

import os
import json
from functools import cached_property
from utils.azclients import AzureClientFactory as acf

class ConfigLoader:
    """
    Singleton class that loads and provides access to application configuration from an Azure Blob.
    
    The configuration is loaded from a JSON file specified by a container and blob name.
    Defaults for these parameters are taken from the environment variables:
      - CONFIG_CONTAINER_NAME (default: "config")
      - CONFIG_BLOB_NAME (default: "app_config.json")
    
    The JSON file should have top-level keys corresponding to target class names.
    
    Public Properties:
      - config: Retrieves the entire configuration dictionary.
    """
    _instance = None

    def __new__(cls):
        """Create and return the singleton instance of ConfigLoader."""
        if cls._instance is None:
            # Create and store the singleton instance
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self, container_name: str = os.environ.get("CONFIG_CONTAINER_NAME", "config"),
                 blob_name: str = os.environ.get("CONFIG_BLOB_NAME", "config.json")):
        """Initialize the ConfigLoader with container and blob names."""
        self.container_name = container_name
        self.blob_name = blob_name

    @cached_property
    def config(self) -> dict:
        """Retrieve the entire configuration dictionary, loading it from Azure Blob storage if necessary."""
        try:
            # Load configuration from Azure Blob storage
            return json.loads(acf.get_instance().download_blob_content(self.container_name, self.blob_name))
        except Exception as e:
            # Raise an AttributeError if the blob fails to load
            raise AttributeError(f"Failed to load configuration from blob '{self.blob_name}' in container '{self.container_name}': {e}") from e

    def get_config(self, target_class: str) -> dict:
        """Retrieve the configuration for the given target class.

        Args:
            target_class (str): The name of the target class.

        Returns:
            dict: The configuration for the target class if available.

        Raises:
            KeyError: If the configuration for the target class is not found.
        """
        if target_class in self.config:
            return self.config[target_class]
        raise KeyError(f"Configuration for '{target_class}' not found.")
