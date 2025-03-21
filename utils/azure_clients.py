"""
This module provides utility classes for creating and managing Azure service clients.

Classes:
    AzureClientFactory: A singleton factory class for creating and managing Azure service clients.
    BlobStorageTokenBackend: A class for handling token storage in Azure Blob Storage.

Functions:
    AzureClientFactory.get_instance: Returns a singleton instance of the AzureClientFactory class.
    AzureClientFactory.get_blob_service_client: Returns a BlobServiceClient using DefaultAzureCredential.
    AzureClientFactory.download_blob_content: Downloads the content of a blob from Azure Blob Storage.
    AzureClientFactory.get_table_service_client: Returns a TableServiceClient using DefaultAzureCredential.
    AzureClientFactory.get_openai_clients: Returns authenticated Azure OpenAI clients.
    AzureClientFactory.get_graph_client: Returns an authenticated Microsoft Graph client using DefaultAzureCredential.
    AzureClientFactory.get_o365_account: Returns an authenticated O365 Account object using DefaultAzureCredential.
    BlobStorageTokenBackend.__init__: Initializes the BlobStorageTokenBackend with container and blob details.
    BlobStorageTokenBackend.load_token: Loads a token from Azure Blob Storage.
    BlobStorageTokenBackend.save_token: Saves a token to Azure Blob Storage.
    BlobStorageTokenBackend.delete_token: Deletes a token from Azure Blob Storage.
    BlobStorageTokenBackend.check_token: Checks the existence of a token in Azure Blob Storage.
"""

import os
import threading
from typing import Optional, Dict
import json

from azure.core.exceptions import (ClientAuthenticationError,
                                   HttpResponseError, ResourceNotFoundError)
from azure.ai.inference import ChatCompletionsClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.data.tables import TableServiceClient
from msgraph import GraphServiceClient

from O365 import Account
from O365.utils import BaseTokenBackend

from utils.logger import configure_logging

# Configure logging
logger = configure_logging(__name__)

class AzureClientFactory:
    """
    A singleton factory class for creating and managing Azure service clients.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        if AzureClientFactory._instance is not None:
            raise RuntimeError("This class is a singleton!")
        self._blob_service_client: BlobServiceClient = None
        self._table_service_client: TableServiceClient = None
        self._openai_clients: Dict[str, ChatCompletionsClient] = {}

        # TODO: Update Graph clients for use with Azure Functions
        self._o365_account: Account = None
        self._graph_client: GraphServiceClient = None

    @classmethod
    def get_instance(cls):
        """
        Returns a singleton instance of the class.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_blob_service_client(self) -> BlobServiceClient:
        """
        Returns a BlobServiceClient using DefaultAzureCredential.
        """
        if self._blob_service_client is None:
            try:
                account_url = os.getenv("AZURE_STORAGEACCOUNT_BLOBENDPOINT")
                if not account_url:
                    raise ValueError("Missing Azure Blob Storage endpoint URL.")

                logger.info("Using DefaultAzureCredential for BlobServiceClient.")
                self._blob_service_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())

                logger.info("✅ BlobServiceClient created successfully.")
            except Exception as e:
                logger.error("❌ BlobServiceClient creation failed: %s", e)
                raise
        return self._blob_service_client

    def download_blob_content(self, container_name: str, blob_name: str) -> Optional[str]:
        """
        Downloads the content of a blob from Azure Blob Storage.

        :param container_name: The name of the container where the blob is stored.
        :param blob_name: The name of the blob to download.
        :return: The content of the blob as a stripped string, or None if an error occurs.
        """
        if not all([container_name, blob_name]):
            logger.error("Container name or blob name is missing.")
            return None

        try:
            content = self.get_blob_service_client().get_blob_client(container=container_name, blob=blob_name).download_blob().readall()
            return content.decode('utf-8').strip()
        except (ResourceNotFoundError, ClientAuthenticationError, HttpResponseError) as e:
            logger.error("Error accessing blob: container=%s, blob=%s, error=%s", container_name, blob_name, e)
        except Exception as e:
            logger.error("Failed to download blob content: container=%s, blob=%s, error=%s, exception=%s",
                         container_name, blob_name, e, e.__class__.__name__)
        return None

    def get_table_service_client(self) -> TableServiceClient:
        """
        Returns a TableServiceClient using DefaultAzureCredential.
        """
        if self._table_service_client is None:
            try:
                account_url = os.getenv("AZURE_STORAGEACCOUNT_TABLEENDPOINT")
                if not account_url:
                    raise ValueError("Missing Azure Table Storage endpoint URL.")

                logger.info("Using DefaultAzureCredential for TableServiceClient.")
                self._table_service_client = TableServiceClient(account_url, credential=DefaultAzureCredential())

                logger.info("✅ TableServiceClient created successfully.")
            except Exception as e:
                logger.error("❌ TableServiceClient creation failed: %s", e)
                raise
        return self._table_service_client

    def get_openai_clients(self) -> Dict[str, ChatCompletionsClient]:
        """
        Returns authenticated Azure OpenAI clients.
        """
        if self._openai_clients is None:
            models = {
                "MODEL_SUMMARY": None,
                "MODEL_LIGHT_SUMMARY": None,
                "MODEL_RANKING": None,
                "MODEL_EMBEDDING_FAST": None,
                "MODEL_EMBEDDING_DEEP": None
            }

            try:
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                for model, _ in models.items():
                    azure_deployment = os.getenv(model)

                    if not all([azure_endpoint, azure_deployment]):
                        raise ValueError(
                            "Missing Azure OpenAI credentials. Check environment variables.")

                    # Use DefaultAzureCredential to get the token
                    # This approach leverages Azure's managed identity to obtain a token securely
                    # This enhances operational security by avoiding the need to manage and rotate secrets
                    # on the Azure OpenAI account (compute) resource manually.

                    self._openai_clients[model] = ChatCompletionsClient(endpoint=azure_endpoint,
                                                                        credential=DefaultAzureCredential())
                    logger.info("✅ Azure OpenAI %s client %s created successfully.", model, azure_deployment)
            except Exception as e:
                logger.error("❌ Azure OpenAI client creation failed: %s", e)
                raise
        return self._openai_clients

    # TODO: Update for use with Azure Functions
    def get_graph_client(self) -> GraphServiceClient:
        """
        Returns an authenticated Microsoft Graph client using DefaultAzureCredential.
        """
        if self._graph_client is None:
            try:
                # Instantiate the GraphServiceClient with the credential
                self._graph_client = GraphServiceClient(DefaultAzureCredential())
                logger.info(
                    "✅ Microsoft Graph client authenticated successfully.")
            except Exception as e:
                logger.error(
                    "❌ GraphServiceClient authentication failed: %s", e)
                raise
        return self._graph_client

    # TODO: Update for use with Azure Functions
    def get_o365_account(self) -> Account:
        """
        Returns an authenticated O365 Account object using DefaultAzureCredential.
        """
        if self._o365_account is None:
            try:
                # Use the token to authenticate the O365 Account
                connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                container_name = "token-container"
                blob_name = "o365_token.json"
                token_backend = BlobStorageTokenBackend(container_name, blob_name, connection_string)
                self._o365_account = Account((os.getenv("RSSAP_CLIENT_ID"), os.getenv("RSSAP_CLIENT_SECRET")), 
                                            token_backend=token_backend, tenant_id=os.getenv("RSSAP_TENANT_ID"))
                
                if not self._o365_account.authenticate():
                    raise ClientAuthenticationError("O365 Account authentication failed.")
                
                logger.info("✅ O365 Account authenticated successfully.")
            except Exception as e:
                logger.error("❌ O365 Account authentication failed: %s", e)
                raise
        return self._o365_account

# TODO: Update for use with Azure Functions and fix AI draft
class BlobStorageTokenBackend(BaseTokenBackend):
    """
    A class for handling token storage in Azure Blob Storage.
    """

    def __init__(self, container_name, blob_name, connection_string):
        """
        Initializes the BlobStorageTokenBackend with container and blob details.
        """
        super().__init__()
        self.container_name = container_name
        self.blob_name = blob_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)

    def load_token(self):
        """
        Loads a token from Azure Blob Storage.

        Returns:
            dict: The token data as a dictionary, or None if an error occurs.
        """
        try:
            blob_client = self.container_client.get_blob_client(self.blob_name)
            token_data = blob_client.download_blob().readall()
            return json.loads(token_data)
        except Exception as e:
            logger.error("Failed to load token from blob storage: %s", e)
            return None

    def save_token(self, token):
        """
        Saves a token to Azure Blob Storage.

        :param token: The token data to save.
        """
        try:
            blob_client = self.container_client.get_blob_client(self.blob_name)
            token_data = json.dumps(token)
            blob_client.upload_blob(token_data, overwrite=True)
        except Exception as e:
            logger.error("Failed to save token to blob storage: %s", e)

    def delete_token(self):
        """
        Deletes a token from Azure Blob Storage.
        """
        try:
            self.container_client.get_blob_client(self.blob_name).delete_blob()
        except Exception as e:
            logger.error("Failed to delete token from blob storage: %s", e)

    def check_token(self):
        """
        Checks the existence of a token in Azure Blob Storage.

        Returns:
            bool: True if the token exists, False otherwise.
        """
        try:
            return self.container_client.get_blob_client(self.blob_name).exists()
        except Exception as e:
            logger.error("Failed to check token existence in blob storage: %s", e)
            return False
