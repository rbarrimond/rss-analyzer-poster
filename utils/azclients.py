"""
This module provides utility classes for creating and managing Azure service clients.

Classes:
    AzureClientFactory: A singleton factory class for creating and managing Azure service clients.
    BlobStorageTokenBackend: A class for handling token storage in Azure Blob Storage.

AzureClientFactory Methods:
    get_instance: Returns a singleton instance of the AzureClientFactory class.
    blob_service_client: Property to get or create a BlobServiceClient using DefaultAzureCredential.
    table_service_client: Property to get or create a TableServiceClient using DefaultAzureCredential.
    queue_service_client: Property to get or create a QueueServiceClient using DefaultAzureCredential.
    graph_client: Property to get or create a Microsoft Graph client using DefaultAzureCredential.
    o365_account: Property to get or create an authenticated O365 Account object.
    openai_clients: Property to get or create authenticated Azure OpenAI clients for various models.
    send_to_queue: Sends a payload to an Azure Queue.
    download_blob_content: Downloads the content of a blob from Azure Blob Storage.
    upload_blob_content: Uploads content to a blob in Azure Blob Storage.
    delete_blob: Deletes a blob from Azure Blob Storage.
    table_upsert_entity: Upserts an entity into an Azure Table Storage table.
    table_delete_entity: Deletes an entity from an Azure Table Storage table.

This module follows Azure best practices for authentication and client creation.
"""

import os
import threading
from typing import Any, Dict
import base64
import json

from azure.ai.inference import ChatCompletionsClient
from azure.core.exceptions import ClientAuthenticationError
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
from msgraph import GraphServiceClient
from O365 import Account

from utils.decorators import (log_and_raise_error, log_and_return_default, log_execution_time,
                              trace_class)
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__, os.getenv("LOG_LEVEL", "INFO"))

@trace_class
class AzureClientFactory:
    """
    Singleton class for creating and managing Azure service clients.

    This class provides methods to create and retrieve instances of various Azure service clients,
    including BlobServiceClient, TableServiceClient, OpenAI clients, QueueServiceClient, and more.
    """
    _instance = None  # Holds the singleton instance
    _lock = threading.Lock()  # Ensures thread-safe initialization

    @classmethod
    def get_instance(cls) -> "AzureClientFactory":
        """
        Returns a singleton instance of the AzureClientFactory class.

        Ensures thread-safe initialization of the singleton instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        Initializes the AzureClientFactory instance with default attributes.
        """
        self._blob_service_client: BlobServiceClient = None
        self._table_service_client: TableServiceClient = None
        self._openai_clients: Dict[str, ChatCompletionsClient] = {}
        self._queue_service_client: QueueServiceClient = None
        self._o365_account: Account = None
        self._graph_client: GraphServiceClient = None

    @property
    def blob_service_client(self) -> BlobServiceClient:
        """
        Property to get or create a BlobServiceClient using DefaultAzureCredential.

        :return: An instance of BlobServiceClient.
        """
        if not self._blob_service_client:
            account_url = os.getenv("AZURE_STORAGEACCOUNT_BLOBENDPOINT")
            if not account_url:
                raise ValueError("Missing Azure Blob Storage endpoint URL.")
            self._blob_service_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())
            logger.info("✅ BlobServiceClient created successfully.")
        return self._blob_service_client

    @property
    def table_service_client(self) -> TableServiceClient:
        """
        Property to get or create a TableServiceClient using DefaultAzureCredential.

        :return: An instance of TableServiceClient.
        """
        if not self._table_service_client:
            account_url = os.getenv("AZURE_STORAGEACCOUNT_TABLEENDPOINT")
            if not account_url:
                raise ValueError("Missing Azure Table Storage endpoint URL.")
            self._table_service_client = TableServiceClient(account_url, credential=DefaultAzureCredential())
            logger.info("✅ TableServiceClient created successfully.")
        return self._table_service_client

    @property
    def queue_service_client(self) -> QueueServiceClient:
        """
        Property to get or create a QueueServiceClient using DefaultAzureCredential.

        :return: An instance of QueueServiceClient.
        """
        if not self._queue_service_client:
            queue_endpoint = os.getenv("AZURE_STORAGEACCOUNT_QUEUEENDPOINT")
            if not queue_endpoint:
                raise ValueError("Missing Azure Queue Storage endpoint URL.")
            self._queue_service_client = QueueServiceClient(queue_endpoint, credential=DefaultAzureCredential())
            logger.info("✅ QueueServiceClient created successfully.")
        return self._queue_service_client

    @property
    def graph_client(self) -> GraphServiceClient:
        """
        Property to get or create a Microsoft Graph client using DefaultAzureCredential.

        :return: An instance of GraphServiceClient.
        """
        if not self._graph_client:
            self._graph_client = GraphServiceClient(DefaultAzureCredential())
            logger.info("✅ Microsoft Graph client authenticated successfully.")
        return self._graph_client

    @property
    def o365_account(self) -> Account:
        """
        Property to get or create an authenticated O365 Account object.

        :return: An instance of O365 Account.
        """
        if not self._o365_account:
            self._o365_account = Account(
                (os.getenv("RSSAP_CLIENT_ID"), os.getenv("RSSAP_CLIENT_SECRET")),
                tenant_id=os.getenv("RSSAP_TENANT_ID")
            )
            if not self._o365_account.authenticate():
                raise ClientAuthenticationError("O365 Account authentication failed.")
            logger.info("✅ O365 Account authenticated successfully.")
        return self._o365_account

    @property
    def openai_clients(self) -> Dict[str, ChatCompletionsClient]:
        """
        Property to get or create authenticated Azure OpenAI clients for various models.

        :return: A dictionary of ChatCompletionsClient instances for various models.
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
                    raise ValueError(f"Missing Azure OpenAI credentials for model {model}.")
                self._openai_clients[model] = ChatCompletionsClient(
                    endpoint=azure_endpoint,
                    credential=DefaultAzureCredential()
                )
                logger.info("✅ Azure OpenAI %s client created successfully.", model)
        return self._openai_clients

    @log_execution_time()
    @log_and_return_default(default_value=None, message="Blob download failed")
    def download_blob_content(self, container_name: str, blob_name: str) -> bytes | str:
        """
        Downloads the content of a blob from Azure Blob Storage.

        :param container_name: The name of the container where the blob is stored.
        :param blob_name: The name of the blob to download.
        :return: The content of the blob as a UTF-8 encoded string or bytes.
        :raises ValueError: If container_name or blob_name is missing.
        """
        if not all([container_name, blob_name]):
            raise ValueError(f"Container ({container_name}) or blob ({blob_name}) is missing.")
        
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_properties = blob_client.get_blob_properties()
        content_type = blob_properties['content_settings']['content_type']
        
        content = blob_client.download_blob().readall()
        logger.debug("Blob downloaded %d bytes successfully: container=%s, blob=%s", len(content), container_name, blob_name)

        if content_type.startswith('text/') or content_type in ['application/json', 'application/xml',
                                                                'application/x-yaml', 'application/xhtml+xml']:
            return content.decode('utf-8')
        else:
            return content

    @log_execution_time()
    @log_and_return_default(default_value=None, message="Blob upload failed")
    def upload_blob_content(self, container_name: str, blob_name: str, content: str | bytes) -> Dict[str, Any]:
        """
        Uploads content to a blob in Azure Blob Storage.

        This method uploads the specified content to a blob within the given container in Azure Blob Storage.
        It ensures that the blob is overwritten if it already exists and handles any errors that may occur
        during the upload process.

        :param container_name: The name of the container where the blob will be stored.
        :param blob_name: The name of the blob to upload.
        :param content: The content to upload, which can be a string or bytes.
        :return: A dictionary containing metadata about the uploaded blob.
        :raises ValueError: If container_name, blob_name, or content is missing.
        """
        if not all([container_name, blob_name, content]):
            raise ValueError(f"Container ({container_name}), blob ({blob_name}), or content is missing.")
        
        result = self.blob_service_client.get_blob_client(container=container_name,
                                                          blob=blob_name).upload_blob(content, overwrite=True)
        logger.debug("Blob uploaded to container=%s, blob=%s with result: %s", container_name, blob_name, result)

        return result

    @log_execution_time()
    @log_and_raise_error("Blob delete failed")
    def delete_blob(self, container_name: str, blob_name: str) -> None:
        """
        Deletes a blob from Azure Blob Storage.

        This method deletes the specified blob from the given container in Azure Blob Storage.
        It handles any errors that may occur during the deletion process.

        :param container_name: The name of the container where the blob is stored.
        :param blob_name: The name of the blob to delete.
        :raises ValueError: If container_name or blob_name is missing.
        """
        if not all([container_name, blob_name]):
            raise ValueError(f"Container ({container_name}) or blob ({blob_name}) is missing.")
        
        result = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name).delete_blob()
        logger.debug("Blob deleted from container=%s, blob=%s with result: %s", container_name, blob_name, result)

    @log_execution_time()
    @log_and_raise_error("Table entity upsert failed")
    def table_upsert_entity(self, table_name: str, entity: dict) -> dict:
        """
        Upserts an entity into an Azure Table Storage table.

        This function upserts the specified entity into a table within Azure Table Storage.
        It ensures that the entity is added or updated as needed and handles any errors that may occur
        during the process.

        :param table_name: The name of the table where the entity will be upserted.
        :param entity: The entity to upsert, represented as a dictionary.
        :return: A dictionary containing metadata about the upserted entity.
        :raises ValueError: If table_name or entity is missing.
        """
        if not all([table_name, entity]):
            raise ValueError("Table name or entity is missing.")

        table_client = self.table_service_client.get_table_client(table_name)
        result = table_client.upsert_entity(entity)
        logger.debug("Entity table=%s, entity=%s upserted with result %s", table_name, entity, result)
        
        return result
    
    @log_execution_time()
    @log_and_raise_error("Table entity delete failed")
    def table_delete_entity(self, table_name: str, entity: dict) -> None:
        """
        Deletes an entity from an Azure Table Storage table.

        This function deletes the specified entity from a table within Azure Table Storage.
        It handles any errors that may occur during the deletion process.

        :param table_name: The name of the table where the entity will be deleted.
        :param entity: The entity to delete, represented as a dictionary.
        :raises ValueError: If table_name or entity is missing.
        """
        if not all([table_name, entity]):
            raise ValueError("Table name or entity is missing.")

        table_client = self.table_service_client.get_table_client(table_name)
        result = table_client.delete_entity(entity)
        logger.debug("Entity table=%s, entity=%s deleted with result %s", table_name, entity, result)
        
        return result

    def send_to_queue(self, queue_name: str, payload: dict) -> None:
        """
        Sends a payload to an Azure Queue.

        This method encodes the given payload as a base64 string and sends it to the specified Azure Queue.

        Args:
            queue_name (str): The name of the Azure Queue.
            payload (dict): The dictionary payload to encode and send.

        Raises:
            ValueError: If the queue client cannot be created or the queue name is invalid.
        """
        queue_client: QueueServiceClient = self.queue_service_client.get_queue_client(queue_name)
        if not queue_client:
            raise ValueError(f"Unable to create queue client named {queue_name}.")

        encoded_payload = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')
        message = queue_client.send_message(encoded_payload)

        logger.debug("Payload sent to queue: %s", payload)
        logger.debug("Queue message sent: %s", message)
