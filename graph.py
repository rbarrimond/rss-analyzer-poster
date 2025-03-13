import os
import logging
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

# Load credentials from environment variables or configuration
TENANT_ID = os.getenv("RSSAP_TENANT_ID", "AZURE_TENANT_ID")
CLIENT_ID = os.getenv("RSSAP_CLIENT_ID", "AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("RSSAP_CLIENT_SECRET", "AZURE_CLIENT_SECRET")

def get_graph_client() -> GraphServiceClient:
    """ Returns an authenticated Microsoft Graph client using Client Credentials """
    try:
        if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
            raise ValueError(
                "Missing Azure AD credentials. Check environment variables.")

        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )

        client = GraphServiceClient(credential)
        logging.info("✅ Microsoft Graph client authenticated successfully.")
        return client

    except Exception as e:
        logging.error("❌ GraphServiceClient authentication failed: %s", e)
        raise
