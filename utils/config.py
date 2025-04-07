"""Module providing the ConfigLoader class for loading configuration from Azure Blob storage."""

import os
import json
from utils.azclients import AzureClientFactory as acf
from utils.decorators import trace_class

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

    def __new__(cls):
        """Create and return the singleton instance of ConfigLoader."""
        if cls._instance is None:
            # Create and store the singleton instance
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self, container_name: str = os.environ.get("CONFIG_CONTAINER_NAME", "config"),
                 blob_name: str = os.environ.get("CONFIG_BLOB_NAME", "config.json")):
        """Initialize the ConfigLoader by loading JSON configuration from Azure blob storage."""
        # Avoid reloading if already initialized
        if hasattr(self, 'config_data'):
            return  # already loaded

        self.config_data = json.loads(acf.get_instance().download_blob_content(container_name, blob_name))

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
        try:
            config_data = object.__getattribute__(self, "config_data")
        except AttributeError as e:
            raise AttributeError("'ConfigLoader' object has no attribute 'config_data'") from e
        if name in config_data:
            return config_data[name]
        raise AttributeError(f"'ConfigLoader' object has no attribute '{name}'")
