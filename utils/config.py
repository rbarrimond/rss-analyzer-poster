import os
import json
from utils.azclients import AzureClientFactory
from utils.decorators import log_and_ignore_error, log_and_raise_error, retry_on_failure, trace_class

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
        if cls._instance is None:
            # Create and store the singleton instance
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    @log_and_raise_error("Failed to load config from blob storage.")
    @retry_on_failure(retries=2, delay=1000)
    def __init__(self, container: str = os.environ.get("CONFIG_CONTAINER_NAME", "config"),
                 blob_name: str = os.environ.get("CONFIG_BLOB_NAME", "app_config.json")):
        # Avoid reloading if already initialized
        if hasattr(self, 'config_data'):
            return  # already loaded

        # Use provided container and blob_name parameters (defaulting to environment variables)
        azure_factory = AzureClientFactory.get_instance()
        # Retrieve the blob client using the local variables directly
        blob_client = azure_factory.get_blob_service_client().get_blob_client(
            container=container,
            blob=blob_name
        )
        # Parse the JSON content
        self.config_data = json.loads(
            blob_client.download_blob().readall().decode('utf-8'))

    # Refactor into a property that returns the full configuration.
    @property
    def config(self) -> dict:
        # Return the full configuration dictionary.
        return self.config_data

    # Add __getattr__ to provide property-like access for target class configurations.
    def __getattr__(self, name: str) -> dict:
        # Return the configuration for the target class if available.
        if name in self.config_data:
            return self.config_data[name]
        raise AttributeError(f"'ConfigLoader' object has no attribute '{name}'")
