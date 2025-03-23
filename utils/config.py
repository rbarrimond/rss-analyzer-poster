import os
import json
from utils.azure_clients import AzureClientFactory
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
        self.container = container
        self.blob_name = blob_name
        azure_factory = AzureClientFactory.get_instance()
        # Retrieve the blob client using the provided container and blob_name
        blob_client = azure_factory.get_blob_service_client().get_blob_client(
            container=self.container,
            blob=self.blob_name
        )
        content = blob_client.download_blob().readall()
        # Parse the JSON content
        self.config_data = json.loads(content.decode('utf-8'))

    @log_and_ignore_error("Failed to get configuration.")
    def get_config(self, target_class: str) -> dict:
        """
        Retrieves the configuration dictionary for the specified target class name.
        
        Args:
            target_class (str): The name of the target class whose configuration is requested.
        
        Returns:
            dict: The configuration object for the target class, or empty dict if not found.
        """
        # Return configuration for the given class; default to empty dict if not present.
        return self.config_data.get(target_class, {})
