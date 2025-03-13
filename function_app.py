"""
Azure Function App

This module defines the Azure Functions for collecting and analyzing RSS feeds:
1. rssAnalyzerPoster - Scheduled to run daily at 6 AM (UTC) to fetch new RSS feeds, store them in 
   Microsoft Lists, and analyze them using Azure OpenAI.
2. rssAnalyzerPosterHttp - HTTP-triggered endpoint to fetch and analyze RSS feeds on-demand.
3. rssSummarizerHttp - HTTP-triggered endpoint to summarize existing RSS articles without fetching new ones.
4. rssPosterHttp - HTTP-triggered endpoint to fetch RSS feeds without analyzing them.

Dependencies:
- Uses Azure Blob Storage for storing configuration files and role content.
- Integrates with Microsoft Graph API to interact with Microsoft Lists.
- Utilizes Azure OpenAI for generating summaries and engagement scores.

Environment Variables:
- Various environment variables are used for configuration, including Azure Blob Storage endpoints, 
  SharePoint site and list IDs, and Azure Key Vault URL for secrets.

Key Operations:
- Fetching RSS feeds from URLs specified in a configuration file stored in Azure Blob Storage.
- Storing RSS feed entries in Microsoft Lists.
- Analyzing and summarizing RSS feed entries using Azure OpenAI and updating Microsoft Lists with the results.

Logging:
- Logging is configured to provide detailed information about the operations performed by each function.
"""

import logging
import os

import azure.functions as func
from azure.functions import HttpRequest, HttpResponse
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from graph import get_graph_client

from rss_processor import (analyze_and_update_recent_articles,
                           process_and_store_feeds)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create the Azure Functions application instance
app = func.FunctionApp()

#
# Global constants initialized by environment variables
#

# Azure Blob Storage endpoint for accessing blobs
AZURE_STORAGEACCOUNT_BLOBENDPOINT = os.getenv('AZURE_STORAGEACCOUNT_BLOBENDPOINT')

# SharePoint site ID where Microsoft Lists are stored
SITE_ID = os.getenv('SITE_ID')

# Microsoft List ID for storing and managing RSS feed entries
LIST_ID = os.getenv('LIST_ID')

# Container and blob names for configuration and role content
CONFIG_CONTAINER_NAME = os.getenv('CONFIG_CONTAINER_NAME')           # Container for configuration files
CONFIG_BLOB_NAME = os.getenv('CONFIG_BLOB_NAME')                     # Blob with RSS feed URLs
SYSTEM_CONTAINER_NAME = os.getenv('SYSTEM_CONTAINER_NAME')           # Container for system role content
SYSTEM_BLOB_NAME = os.getenv('SYSTEM_BLOB_NAME')                     # Blob for system role content used in OpenAI chat completions
USER_CONTAINER_NAME = os.getenv('USER_CONTAINER_NAME')               # Container for user role content
USER_BLOB_NAME = os.getenv('USER_BLOB_NAME')                         # Blob for user role content used in OpenAI chat completions

# Initialize BlobServiceClient for Azure Blob Storage operations
blob_service_client = BlobServiceClient(
    account_url=AZURE_STORAGEACCOUNT_BLOBENDPOINT,
    credential=DefaultAzureCredential()
)

# Initialize Microsoft Graph client for accessing Microsoft Lists
graph_client = get_graph_client()

@app.function_name(name="rssAnalyzerPoster")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
def rss_analyzer_poster(myTimer: func.TimerRequest) -> None:
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
@app.route(route="analyze", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_analyzer_poster_http(req: HttpRequest) -> HttpResponse:
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
@app.route(route="summarize", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_summarizer_http(req: HttpRequest) -> HttpResponse:
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
@app.route(route="collect", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_poster_http(req: HttpRequest) -> HttpResponse:
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
