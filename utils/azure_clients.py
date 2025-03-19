import os
import threading
from typing import Optional

from azure.core.exceptions import (ClientAuthenticationError,
                                   HttpResponseError, ResourceNotFoundError)
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from msgraph import GraphServiceClient
from O365 import Account
from openai import AzureOpenAI

from utils.logger import configure_logging

# Configure logging
logger = configure_logging(__name__)

# Load credentials from environment variables or configuration
TENANT_ID = os.getenv("RSSAP_TENANT_ID", "AZURE_TENANT_ID")
CLIENT_ID = os.getenv("RSSAP_CLIENT_ID", "AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("RSSAP_CLIENT_SECRET", "AZURE_CLIENT_SECRET")


class AzureClientFactory:
    """
    AzureClientFactory is responsible for creating and managing Azure service clients.

    This class implements the singleton pattern to ensure only one instance of the factory exists.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        if AzureClientFactory._instance is not None:
            raise RuntimeError("This class is a singleton!")
        self._graph_client = None
        self._blob_service_client = None
        self._openai_client = None
        self._o365_account = None

    @classmethod
    def get_instance(cls):
        """
        Returns a singleton instance of the class.

        This method ensures that only one instance of the class is created.
        If the instance does not exist, it creates one in a thread-safe manner.

        Returns:
            cls: The singleton instance of the class.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def get_graph_client(self) -> GraphServiceClient:
        """
        Returns an authenticated Microsoft Graph client using Client Credentials.
        """
        if self._graph_client is None:
            try:
                # Check if all required credentials are available
                if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
                    raise ValueError(
                        "Missing Azure AD credentials. Check environment variables.")

                # Create a ClientSecretCredential object using the loaded credentials
                credential = ClientSecretCredential(
                    tenant_id=TENANT_ID,
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET
                )

                # Instantiate the GraphServiceClient with the credential
                self._graph_client = GraphServiceClient(credential)
                logger.info(
                    "✅ Microsoft Graph client authenticated successfully.")
            except Exception as e:
                logger.error(
                    "❌ GraphServiceClient authentication failed: %s", e)
                raise
        return self._graph_client

    async def get_blob_service_client(self) -> BlobServiceClient:
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

    async def get_openai_client(self) -> AzureOpenAI:
        """
        Returns an authenticated Azure OpenAI client.
        """
        if self._openai_client is None:
            try:
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
                api_version = os.getenv("OPENAI_API_VERSION")

                if not all([azure_endpoint, azure_deployment, api_version]):
                    raise ValueError(
                        "Missing Azure OpenAI credentials. Check environment variables.")

                # Use DefaultAzureCredential to get the token
                # This approach leverages Azure's managed identity to obtain a token securely
                # This enhances operational security by avoiding the need to manage and rotate secrets
                # on the Azure OpenAI account (compute) resource manually.
                token = DefaultAzureCredential().get_token("https://cognitiveservices.azure.com/.default")

                self._openai_client = AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    azure_deployment=azure_deployment,
                    api_version=api_version,
                    api_key=token.token  # Pass the obtained token to the AzureOpenAI client
                )
                logger.info("✅ Azure OpenAI client created successfully.")
            except Exception as e:
                logger.error("❌ Azure OpenAI client creation failed: %s", e)
                raise
        return self._openai_client

    async def get_o365_account(self) -> Account:
        """
        Returns an authenticated O365 Account object using the same credentials as the Graph client.
        """
        if self._o365_account is None:
            try:
                if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
                    raise ValueError(
                        "Missing Azure AD credentials. Check environment variables.")

                credentials = (CLIENT_ID, CLIENT_SECRET)
                self._o365_account = Account(
                    credentials, auth_flow_type="credentials", tenant_id=TENANT_ID)
                if not self._o365_account.authenticate():
                    raise ClientAuthenticationError(
                        "O365 Account authentication failed.")
                logger.info("✅ O365 Account authenticated successfully.")
            except Exception as e:
                logger.error("❌ O365 Account authentication failed: %s", e)
                raise
        return self._o365_account

    async def download_blob_content(self, container_name: str, blob_name: str) -> Optional[str]:
        """
        Downloads the content of a blob from Azure Blob Storage, decodes it to UTF-8,
        and returns it as a stripped string.

        :param container_name: The name of the container where the blob is stored.
        :param blob_name: The name of the blob to download.
        :return: The content of the blob as a stripped string, or None if an error occurs.
        """
        if not container_name or not blob_name:
            logger.error("Container name or blob name is missing.")
            return None

        try:
            blob_service_client = await self.get_blob_service_client()
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name)
            blob_content = await blob_client.download_blob()
            content = await blob_content.readall()
            return content.decode('utf-8').strip()
        except ResourceNotFoundError:
            logger.error("Blob not found: container=%s, blob=%s",
                         container_name, blob_name)
        except ClientAuthenticationError:
            logger.error("Authentication error while accessing blob: container=%s, blob=%s",
                         container_name, blob_name)
        except HttpResponseError as e:
            logger.error("HTTP response error while accessing blob: container=%s, blob=%s, error=%s",
                         container_name, blob_name, e)
        except Exception as e:
            logger.error("Failed to download blob content: %s", e)
        return None
