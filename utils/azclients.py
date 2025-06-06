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

import base64
import io
import json
import os
import threading
from functools import lru_cache
from typing import Any, Dict, Optional

import numpy as np
from azure.ai.inference import ChatCompletionsClient
from azure.core.exceptions import ClientAuthenticationError
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
from msgraph import GraphServiceClient
from O365 import Account

from utils.decorators import log_and_raise_error
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__, os.getenv("LOG_LEVEL", "INFO"))

# Define a module-level constant for the sentinel value
NULL_CONTENT = "\ue000"  # Unicode private use character for missing content


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
            self._blob_service_client = BlobServiceClient(
                account_url, credential=DefaultAzureCredential())
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
            self._table_service_client = TableServiceClient(
                account_url, credential=DefaultAzureCredential())
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
            self._queue_service_client = QueueServiceClient(
                queue_endpoint, credential=DefaultAzureCredential())
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
                raise ClientAuthenticationError(
                    "O365 Account authentication failed.")
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
                    raise ValueError(
                        f"Missing Azure OpenAI credentials for model {model}.")
                self._openai_clients[model] = ChatCompletionsClient(
                    endpoint=azure_endpoint,
                    credential=DefaultAzureCredential()
                )
                logger.info(
                    "✅ Azure OpenAI %s client created successfully.", model)
        return self._openai_clients

    @log_and_raise_error(message="Failed to download blob content")
    @lru_cache(maxsize=100)  # Cache results for up to 100 blobs
    def download_blob_content(self, container_name: str, blob_name: str) -> bytes | str | None:
        """
        Downloads the content of a blob from Azure Blob Storage.

        :param container_name: The name of the container where the blob is stored.
        :param blob_name: The name of the blob to download.
        :return: The content of the blob as a UTF-8 encoded string or bytes.
        :raises ValueError: If container_name or blob_name is missing.
        """
        if not all([container_name, blob_name]):
            raise ValueError(
                f"Container ({container_name}) or blob ({blob_name}) is missing.")

        if blob_name in self.blob_service_client.get_container_client(container_name).list_blob_names():
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name)
            blob_properties = blob_client.get_blob_properties()
            content_type = blob_properties['content_settings']['content_type']

            content = blob_client.download_blob().readall()
            logger.debug("Blob downloaded %d bytes successfully: container=%s, blob=%s", len(
                content), container_name, blob_name)

            if content_type.startswith('text/') or content_type in ['application/json', 'application/xml',
                                                                    'application/x-yaml', 'application/xhtml+xml']:
                return content.decode('utf-8')
            else:
                return content
        else:
            logger.warning("Blob not found: container=%s, blob=%s",
                           container_name, blob_name)
            return None

    @log_and_raise_error(message="Failed to upload blob content")
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
            raise ValueError(
                f"Container ({container_name}), blob ({blob_name}), or content is missing.")

        result = self.blob_service_client.get_blob_client(container=container_name,
                                                          blob=blob_name).upload_blob(content, overwrite=True)
        logger.debug("Blob uploaded to container=%s, blob=%s with result: %s",
                     container_name, blob_name, result)

        return result

    @log_and_raise_error(message="Failed to delete blob")
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
            raise ValueError(
                f"Container ({container_name}) or blob ({blob_name}) is missing.")

        result = self.blob_service_client.get_blob_client(
            container=container_name, blob=blob_name).delete_blob()
        logger.debug("Blob deleted from container=%s, blob=%s with result: %s",
                     container_name, blob_name, result)

    @log_and_raise_error(message="Failed to upsert entity in table")
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
        logger.debug("Entity table=%s, entity=%s upserted with result %s",
                     table_name, entity, result)

        return result

    @log_and_raise_error(message="Failed to delete entity from table")
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
        logger.debug("Entity table=%s, entity=%s deleted with result %s",
                     table_name, entity, result)

        return result

    @log_and_raise_error(message="Failed to send payload to queue")
    def send_to_queue(self, queue_name: str, payload: dict) -> None:
        """
        Sends a payload to an Azure Queue.

        This method encodes the given payload as a base64 string and sends it to the specified Azure Queue.
        It uses the QueueServiceClient to interact with the Azure Queue Storage.

        :param queue_name: The name of the Azure Queue.
        :param payload: The dictionary payload to encode and send as a message.
        :raises ValueError: If the queue client cannot be created or the queue name is invalid.
        """
        queue_client: QueueServiceClient = self.queue_service_client.get_queue_client(
            queue_name)

        # Encode the payload as a base64 string to ensure it is safely transmitted over the queue.
        # Azure Storage Queues expect messages to be UTF-8 encoded strings with a maximum size of 64 KB.
        # By encoding the payload as base64, we ensure that any special characters or binary data
        # in the JSON payload are safely converted into a string format that can be transmitted.
        encoded_payload = base64.b64encode(
            json.dumps(payload).encode('utf-8')).decode('utf-8')
        message = queue_client.send_message(encoded_payload)

        logger.debug("Payload sent to queue: %s", payload)
        logger.debug("Queue message sent: %s", message)


class BlobContentMixin:
    """Mixin class for handling Azure Blob Storage content."""
    _content_cache: Optional[Any] = None
    _blob_lock: threading.Lock = threading.Lock()

    @property
    def blob_container(self) -> str:
        """The name of the Azure Blob Storage container."""
        raise NotImplementedError("Subclasses must define the blob_container")

    @property
    def blob_path(self) -> str:
        """The path to the blob in Azure Blob Storage."""
        raise NotImplementedError("Subclasses must define the blob_path")

    def load_blob(self) -> Optional[Any]:
        """
        Loads the content of the blob from Azure Blob Storage.
        This method caches the content for subsequent calls to avoid redundant downloads.
        :return: The content of the blob as bytes or None if not found.
        """
        if self._content_cache is not None:
            return self._content_cache

        with self._blob_lock:
            logger.debug("Loading blob: %s", self.blob_path)
            blob = AzureClientFactory.get_instance().download_blob_content(
                container_name=self.blob_container, blob_name=self.blob_path
            )
            self._content_cache = blob or NULL_CONTENT
            return self._content_cache

    def save_blob(self, content: Any) -> None:
        """
        Saves the content to the blob in Azure Blob Storage.
        :param content: The content to save, which can be a string or bytes.
        :raises ValueError: If content is None or empty.
        """
        if not content:
            raise ValueError("No content provided to save.")
        AzureClientFactory.get_instance().upload_blob_content(
            container_name=self.blob_container,
            blob_name=self.blob_path,
            content=content,
        )
        logger.debug("Saved blob to %s/%s", self.blob_container, self.blob_path)

    def delete_blob(self) -> None:
        """
        Deletes the blob from Azure Blob Storage.
        This method removes the blob from the specified container.
        """
        AzureClientFactory.get_instance().delete_blob(
            container_name=self.blob_container, blob_name=self.blob_path
        )
        logger.debug("Deleted blob %s/%s", self.blob_container, self.blob_path)

class MarkdownBlobMixin(BlobContentMixin):
    """Specialized mixin for handling Markdown text blobs."""
    # pylint: disable=abstract-method
    def load_blob(self) -> Optional[str]:
        blob = super().load_blob()
        if isinstance(blob, bytes):
            return blob.decode("utf-8")
        return blob

    def save_blob(self, content: str) -> None:
        if not isinstance(content, str):
            raise ValueError("Expected string content for Markdown blob.")
        super().save_blob(content.encode("utf-8"))


class NumpyBlobMixin(BlobContentMixin):
    """Specialized mixin for handling NumPy .npy blobs."""
    # pylint: disable=abstract-method
    def load_blob(self) -> Optional[np.ndarray]:
        blob = super().load_blob()
        if not blob or blob == NULL_CONTENT:
            return None
        return np.load(io.BytesIO(blob), allow_pickle=True)

    def save_blob(self, content: np.ndarray) -> None:
        if content is None:
            raise ValueError("No embeddings provided to save.")
        buffer = io.BytesIO()
        np.save(buffer, content)
        buffer.seek(0)
        super().save_blob(buffer.read())
