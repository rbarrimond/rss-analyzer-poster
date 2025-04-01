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
from typing import Dict
import json

from azure.core.exceptions import ClientAuthenticationError
from azure.ai.inference import ChatCompletionsClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.data.tables import TableServiceClient
from azure.storage.queue import QueueServiceClient

from msgraph import GraphServiceClient

from O365 import Account
from O365.utils import BaseTokenBackend

from utils.logger import LoggerFactory
from utils.decorators import log_and_raise_error, log_execution_time, retry_on_failure, trace_class

logger = LoggerFactory.get_logger(__name__, os.getenv("LOG_LEVEL", "INFO"))

@trace_class
class AzureClientFactory:
    """
    A singleton factory class for creating and managing Azure service clients.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        # Initialize the instance normally without raising an error.
        self._blob_service_client: BlobServiceClient = None
        self._table_service_client: TableServiceClient = None
        self._openai_clients: Dict[str, ChatCompletionsClient] = {}
        self._queue_service_client: QueueServiceClient = None  # new attribute

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

    @log_and_raise_error("❌ BlobServiceClient creation failed.")
    def get_blob_service_client(self) -> BlobServiceClient:
        """
        Returns a BlobServiceClient using DefaultAzureCredential.
        """
        if not self._blob_service_client:
            account_url = os.getenv("AZURE_STORAGEACCOUNT_BLOBENDPOINT")
            if not account_url:
                raise ValueError("Missing Azure Blob Storage endpoint URL.")

            self._blob_service_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())
            logger.info("✅ BlobServiceClient created successfully.")

        return self._blob_service_client

    @log_execution_time()
    @log_and_raise_error("❌ Blob download failed.")
    @retry_on_failure(retries=1, delay=500)
    def download_blob_content(self, container_name: str, blob_name: str) -> str:
        """
        Downloads the content of a blob from Azure Blob Storage.

        :param container_name: The name of the container where the blob is stored.
        :param blob_name: The name of the blob to download.
        :return: The content of the blob as a stripped string, or None if an error occurs.
        """
        if not all([container_name, blob_name]):
            logger.error("Container name or blob name is missing. container=%s, blob=%s", container_name, blob_name)
            raise ValueError("Container name or blob name is missing.")
        
        logger.info("Downloading blob: container=%s, blob=%s", container_name, blob_name)
        content = self.get_blob_service_client().get_blob_client(container=container_name, blob=blob_name).download_blob().readall()
        return content.decode('utf-8').strip()

    @log_and_raise_error("❌ TableServiceClient creation failed.")
    def get_table_service_client(self) -> TableServiceClient:
        """
        Returns a TableServiceClient using DefaultAzureCredential.
        """
        if not self._table_service_client:
            account_url = os.getenv("AZURE_STORAGEACCOUNT_TABLEENDPOINT")
            if not account_url:
                raise ValueError("Missing Azure Table Storage endpoint URL.")

            self._table_service_client = TableServiceClient(account_url, credential=DefaultAzureCredential())
            logger.info("✅ TableServiceClient created successfully.")

        return self._table_service_client

    @log_and_raise_error("❌ Azure OpenAI client creation failed.")
    def get_openai_clients(self) -> Dict[str, ChatCompletionsClient]:
        """
        Returns authenticated Azure OpenAI clients.
        """
        if not self._openai_clients:
            models = {
                "MODEL_SUMMARY": None,
                "MODEL_LIGHT_SUMMARY": None,
                "MODEL_RANKING": None,
                "MODEL_EMBEDDING_FAST": None,
                "MODEL_EMBEDDING_DEEP": None
            }
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

            for model, _ in models.items():
                azure_deployment = os.getenv(model)
                if not all([azure_endpoint, azure_deployment]):
                    raise ValueError("Missing Azure OpenAI credentials. Check environment variables.")
                self._openai_clients[model] = ChatCompletionsClient(endpoint=azure_endpoint,
                                                                    credential=DefaultAzureCredential())
                logger.info("✅ Azure OpenAI %s client %s created successfully.", model, azure_deployment)

        return self._openai_clients

    @log_and_raise_error("❌ QueueServiceClient creation failed.")
    def get_queue_service_client(self) -> QueueServiceClient:
        """
        Returns an instance of QueueServiceClient using DefaultAzureCredential.
        
        Returns:
            QueueServiceClient: The QueueServiceClient instance.
        """
        if not self._queue_service_client:
            queue_endpoint = os.getenv("AZURE_STORAGEACCOUNT_QUEUEENDPOINT")
            if not queue_endpoint:
                raise ValueError("Missing Azure Queue Storage endpoint URL.")
            self._queue_service_client = QueueServiceClient(queue_endpoint, credential=DefaultAzureCredential())
            logger.info("✅ QueueServiceClient created successfully.")
        return self._queue_service_client

    @log_and_raise_error("❌ GraphServiceClient authentication failed.")
    def get_graph_client(self) -> GraphServiceClient:
        """
        Returns an authenticated Microsoft Graph client using DefaultAzureCredential.
        """
        if not self._graph_client:
            self._graph_client = GraphServiceClient(DefaultAzureCredential())
            logger.info("✅ Microsoft Graph client authenticated successfully.")
        return self._graph_client

    @log_and_raise_error("❌ O365 Account authentication failed.")
    def get_o365_account(self) -> Account:
        """
        Returns an authenticated O365 Account object using DefaultAzureCredential.
        """
        if self._o365_account is None:
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

    @retry_on_failure()
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

    @retry_on_failure()
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

    @retry_on_failure()
    def delete_token(self):
        """
        Deletes a token from Azure Blob Storage.
        """
        try:
            self.container_client.get_blob_client(self.blob_name).delete_blob()
        except Exception as e:
            logger.error("Failed to delete token from blob storage: %s", e)

    @retry_on_failure()
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
