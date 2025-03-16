import logging
import os
import threading
from typing import Optional
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError, HttpResponseError
from msgraph import GraphServiceClient
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
                    raise ValueError("Missing Azure AD credentials. Check environment variables.")

                # Create a ClientSecretCredential object using the loaded credentials
                credential = ClientSecretCredential(
                    tenant_id=TENANT_ID,
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET
                )

                # Instantiate the GraphServiceClient with the credential
                self._graph_client = GraphServiceClient(credential)
                logger.info("✅ Microsoft Graph client authenticated successfully.")
            except Exception as e:
                logger.error("❌ GraphServiceClient authentication failed: %s", e)
                raise
        return self._graph_client

    async def get_blob_service_client(self) -> BlobServiceClient:
        """
        Returns a BlobServiceClient with the selected credential type.
        """
        if self._blob_service_client is None:
            try:
                account_url = os.getenv("AZURE_STORAGEACCOUNT_BLOBENDPOINT")
                if not account_url:
                    raise ValueError("Missing Azure Blob Storage endpoint URL.")
                logger.info("Using account URL: %s", account_url)

                if account_url.startswith("http://127.0.0.1:10000"):
                    # Use the local development storage account with connection string
                    # Not a secure way to store connection strings, only for local development
                    # Azurite storage emulator must be running
                    connection_string = (
                        "DefaultEndpointsProtocol=http;"
                        "AccountName=devstoreaccount1;"
                        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
                        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
                    )
                    logger.info("Using connection string for local Azurite storage.")
                    self._blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                else:
                    # Ensure the account URL uses HTTPS
                    if not account_url.startswith("https://"):
                        raise ValueError("Token credential is only supported with HTTPS.")
                    logger.info("Using DefaultAzureCredential for authentication.")
                    # Return a BlobServiceClient instance
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
                api_key = os.getenv("AZURE_OPENAI_API_KEY")

                if not all([azure_endpoint, azure_deployment, api_version, api_key]):
                    raise ValueError("Missing Azure OpenAI credentials. Check environment variables.")

                self._openai_client = AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    azure_deployment=azure_deployment,
                    api_version=api_version,
                    api_key=api_key
                )
                logger.info("✅ Azure OpenAI client created successfully.")
            except Exception as e:
                logger.error("❌ Azure OpenAI client creation failed: %s", e)
                raise
        return self._openai_client

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
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_content = await blob_client.download_blob()
            content = await blob_content.readall()
            return content.decode('utf-8').strip()
        except ResourceNotFoundError:
            logger.error("Blob not found: container=%s, blob=%s", container_name, blob_name)
        except ClientAuthenticationError:
            logger.error("Authentication error while accessing blob: container=%s, blob=%s",
                         container_name, blob_name)
        except HttpResponseError as e:
            logger.error("HTTP response error while accessing blob: container=%s, blob=%s, error=%s",
                         container_name, blob_name, e)
        except Exception as e:
            logger.error("Failed to download blob content: %s", e)
        return None
