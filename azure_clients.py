import logging
import os
from typing import Optional
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError, HttpResponseError
from msgraph import GraphServiceClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load credentials from environment variables or configuration
TENANT_ID = os.getenv("RSSAP_TENANT_ID", "AZURE_TENANT_ID")
CLIENT_ID = os.getenv("RSSAP_CLIENT_ID", "AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("RSSAP_CLIENT_SECRET", "AZURE_CLIENT_SECRET")

def get_graph_client() -> GraphServiceClient:
    """ Returns an authenticated Microsoft Graph client using Client Credentials """
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
        client = GraphServiceClient(credential)
        logging.info("✅ Microsoft Graph client authenticated successfully.")
        return client

    except Exception as e:
        logging.error("❌ GraphServiceClient authentication failed: %s", e)
        raise

def get_blob_service_client() -> BlobServiceClient:
    """Returns a BlobServiceClient with the selected credential type."""
    try:
        account_url = os.getenv("AZURE_STORAGEACCOUNT_BLOBENDPOINT")
        if not account_url:
            raise ValueError("Missing Azure Blob Storage endpoint URL.")
        logging.info("Using account URL: %s", account_url)

        if account_url.startswith("http://127.0.0.1:10000"):
            # Use the local development storage account with connection string
            connection_string = (
                "DefaultEndpointsProtocol=http;"
                "AccountName=devstoreaccount1;"
                "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCD9HHqRSdA=;"
                "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
            )
            logging.info("Using connection string for local Azurite storage.")
            client = BlobServiceClient.from_connection_string(connection_string)
        else:
            # Ensure the account URL uses HTTPS
            if not account_url.startswith("https://"):
                raise ValueError("Token credential is only supported with HTTPS.")
            logging.info("Using DefaultAzureCredential for authentication.")
            # Return a BlobServiceClient instance
            client = BlobServiceClient(account_url, credential=DefaultAzureCredential())

        logging.info("✅ BlobServiceClient created successfully.")
        return client

    except Exception as e:
        logging.error("❌ BlobServiceClient creation failed: %s", e)
        raise

def download_blob_content(blob_service_client: BlobServiceClient, container_name: str, blob_name: str) -> Optional[str]:
    """
    Downloads the content of a blob from Azure Blob Storage and returns it as a string.

    :param blob_service_client: The BlobServiceClient instance to interact with Azure Blob Storage.
    :param container_name: The name of the container where the blob is stored.
    :param blob_name: The name of the blob to download.
    :return: The content of the blob as a string, or None if an error occurs.
    """
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob().readall()
        content = blob_data.decode('utf-8').strip()
        return content
    except ResourceNotFoundError:
        logging.error("Blob not found: container=%s, blob=%s", container_name, blob_name)
    except ClientAuthenticationError:
        logging.error("Authentication error while accessing blob: container=%s, blob=%s", container_name, blob_name)
    except HttpResponseError as e:
        logging.error("HTTP response error while accessing blob: container=%s, blob=%s, error=%s", container_name, blob_name, e)
    except Exception as e:
        logging.error("Failed to download blob content: %s", e)
    return None
