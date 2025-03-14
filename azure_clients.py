import logging
import os
from typing import Optional

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from msgraph import GraphServiceClient

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
            client = BlobServiceClient.from_connection_string(connection_string)
        else:
            # Ensure the account URL uses HTTPS
            if not account_url.startswith("https://"):
                raise ValueError("Token credential is only supported with HTTPS.")
            # Return a BlobServiceClient instance
            client = BlobServiceClient(account_url, credential=DefaultAzureCredential())

        logging.info("✅ BlobServiceClient created successfully.")
        return client

    except Exception as e:
        logging.error("❌ BlobServiceClient creation failed: %s", e)
        raise
