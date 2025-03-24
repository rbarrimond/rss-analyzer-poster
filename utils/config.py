"""Module providing the ConfigLoader class for loading configuration from Azure Blob storage."""

import os
import json
from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_raise_error, retry_on_failure, trace_class

@trace_class
class ConfigLoader:
    """
    Singleton class that loads and provides access to application configuration from an Azure Blob.
    
    The configuration is loaded from a JSON file specified by a container and blob name.
    Defaults for these parameters are taken from the environment variables:
      - CONFIG_CONTAINER_NAME (default: "config")
      - CONFIG_BLOB_NAME (default: "app_config.json")
    
    The JSON file should have top-level keys corresponding to target class names.
    
    Public Methods:
      - get_config(target_class: str) -> dict: Retrieves the configuration for the given target class.
    """
    _instance = None

    @log_and_raise_error("Failed to initialize ConfigLoader.")
    def __new__(cls):
        """Create and return the singleton instance of ConfigLoader."""
        if cls._instance is None:
            # Create and store the singleton instance
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    @log_and_raise_error("Failed to load config from blob storage.")
    @retry_on_failure(retries=2, delay=1000)
    def __init__(self, container: str = os.environ.get("CONFIG_CONTAINER_NAME", "config"),
                 blob_name: str = os.environ.get("CONFIG_BLOB_NAME", "app_config.json")):
        """Initialize the ConfigLoader by loading JSON configuration from Azure blob storage."""
        # Avoid reloading if already initialized
        if hasattr(self, 'config_data'):
            return  # already loaded

        # Use provided container and blob_name parameters (defaulting to environment variables)
        # Retrieve the blob client using the local variables directly
        blob_client = acf.get_instance().get_blob_service_client().get_blob_client(
            container=container,
            blob=blob_name
        )
        # Parse the JSON content
        self.config_data = json.loads(
            blob_client.download_blob().readall().decode('utf-8'))

    @property
    def config(self) -> dict:
        """Return the full configuration as a dictionary."""
        return self.config_data

    def __getattr__(self, name: str) -> dict:
        """Provide attribute-like access to target class configurations.
        
        Returns:
            dict: The configuration for the target class if available.
            
        Raises:
            AttributeError: If the configuration for the target class is not found.
        """
        if name in self.config_data:
            return self.config_data[name]
        raise AttributeError(f"'ConfigLoader' object has no attribute '{name}'")
