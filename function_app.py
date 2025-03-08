"""
Azure Function App

This module defines the Azure Functions for collecting and analyzing RSS feeds:
1. rssAnalyzerPoster - Triggered daily at 6 AM (UTC) to fetch new feeds and summarize them.
2. rssAnalyzerPosterHttp - HTTP-triggered endpoint to fetch and summarize feeds on-demand.
3. rssSummarizerHttp - HTTP-triggered endpoint to summarize feeds without fetching new ones.
4. rssPosterHttp - HTTP-triggered endpoint to fetch feeds without analyzing them.

Each function coordinates Cosmos DB access for storage and integrates with Azure OpenAI for
generating article summaries and engagement scores, skipping items that have already been processed.
"""

import os
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from msal import ConfidentialClientApplication
from msgraph.core import GraphClient
from rss_processor import process_and_store_feeds, analyze_and_update_recent_articles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Global constants initialized by environment variables
AZURE_STORAGEACCOUNT_BLOBENDPOINT = os.getenv('AZURE_STORAGEACCOUNT_BLOBENDPOINT')
SITE_ID = os.getenv('SITE_ID')
LIST_ID = os.getenv('LIST_ID')
CONFIG_CONTAINER_NAME = os.getenv('CONFIG_CONTAINER_NAME')
CONFIG_BLOB_NAME = os.getenv('CONFIG_BLOB_NAME')
SYSTEM_CONTAINER_NAME = os.getenv('SYSTEM_CONTAINER_NAME')
SYSTEM_BLOB_NAME = os.getenv('SYSTEM_BLOB_NAME')
USER_CONTAINER_NAME = os.getenv('USER_CONTAINER_NAME')
USER_BLOB_NAME = os.getenv('USER_BLOB_NAME')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')

# Initialize BlobServiceClient
blob_service_client = BlobServiceClient(
    account_url=AZURE_STORAGEACCOUNT_BLOBENDPOINT,
    credential=DefaultAzureCredential()
)

# Initialize Microsoft Graph client
app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET
)
token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
graph_client = GraphClient(credential=token['access_token'])

@app.function_name(name="rssAnalyzerPoster")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
def rssAnalyzerPoster(myTimer: func.TimerRequest) -> None:
    """
    Scheduled Azure Function (runs daily at 6 AM UTC):
    Fetches RSS feeds from configured sources, stores them in Microsoft Lists,
    and analyzes newly stored content with Azure OpenAI, generating summaries and scores.
    """
    logging.info('RSS Analyzer Poster triggered.')
    process_and_store_feeds(
        blob_service_client,
        SITE_ID,
        LIST_ID,
        CONFIG_CONTAINER_NAME,
        CONFIG_BLOB_NAME
    )
    analyze_and_update_recent_articles(
        graph_client,
        SITE_ID,
        LIST_ID,
        blob_service_client,
        SYSTEM_CONTAINER_NAME,
        SYSTEM_BLOB_NAME,
        USER_CONTAINER_NAME,
        USER_BLOB_NAME
    )

@app.function_name(name="rssAnalyzerPosterHttp")
@app.route(route="analyze", methods=["POST"])
def rssAnalyzerPosterHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources, stores them in Microsoft Lists,
    and analyzes each for summaries and scores when invoked externally.
    """
    logging.info('RSS Analyzer Poster HTTP triggered.')
    process_and_store_feeds(
        blob_service_client,
        SITE_ID,
        LIST_ID,
        CONFIG_CONTAINER_NAME,
        CONFIG_BLOB_NAME
    )
    analyze_and_update_recent_articles(
        graph_client,
        SITE_ID,
        LIST_ID,
        blob_service_client,
        SYSTEM_CONTAINER_NAME,
        SYSTEM_BLOB_NAME,
        USER_CONTAINER_NAME,
        USER_BLOB_NAME
    )
    return func.HttpResponse("RSS feeds processed and analyzed successfully.", status_code=200)

@app.function_name(name="rssSummarizerHttp")
@app.route(route="summarize", methods=["POST"])
def rssSummarizerHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Function:
    Summarizes and updates existing RSS articles stored in Microsoft Lists.
    """
    analyze_and_update_recent_articles(
        graph_client,
        SITE_ID,
        LIST_ID,
        blob_service_client,
        SYSTEM_CONTAINER_NAME,
        SYSTEM_BLOB_NAME,
        USER_CONTAINER_NAME,
        USER_BLOB_NAME
    )
    return func.HttpResponse("RSS articles summarized successfully.", status_code=200)

@app.function_name(name="rssPosterHttp")
@app.route(route="collect", methods=["POST"])
def rssPosterHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources and stores them in Microsoft Lists.
    """
    process_and_store_feeds(
        blob_service_client,
        SITE_ID,
        LIST_ID,
        CONFIG_CONTAINER_NAME,
        CONFIG_BLOB_NAME
    )
    return func.HttpResponse("RSS feeds collected and stored successfully.", status_code=200)
