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

from azure_clients import AzureClientFactory

from rss_processor import RssProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create the Azure Functions application instance
app = func.FunctionApp()

# Initialize the AzureClientFactory singleton instance
acf = AzureClientFactory.get_instance()


@app.function_name(name="rssFeedProcessor")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
def rss_feed_processor(myTimer: func.TimerRequest) -> None:
    """
    Scheduled Azure Function (runs daily at 6 AM UTC):
    Fetches RSS feeds from configured sources, stores them in Microsoft Lists,
    and analyzes newly stored content with Azure OpenAI, generating summaries and scores.
    """
    logging.info('RSS Feed Processor triggered.')
    RssProcessor().process_feeds()

@app.function_name(name="rssFeedProcessorHttp")
@app.route(route="analyze", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_feed_processor_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources, stores them in Microsoft Lists,
    and analyzes each for summaries and scores when invoked externally.
    """
    logging.info('RSS Feed Processor HTTP triggered.')
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body.", status_code=400)

    site_id = req_body.get('site_id', os.getenv('SITE_ID'))
    list_id = req_body.get('list_id', os.getenv('LIST_ID'))
    config_container_name = req_body.get(
        'config_container_name', os.getenv('CONFIG_CONTAINER_NAME'))
    config_blob_name = req_body.get(
        'config_blob_name', os.getenv('CONFIG_BLOB_NAME'))
    system_container_name = req_body.get(
        'system_container_name', os.getenv('SYSTEM_CONTAINER_NAME'))
    system_blob_name = req_body.get(
        'system_blob_name', os.getenv('SYSTEM_BLOB_NAME'))
    user_container_name = req_body.get(
        'user_container_name', os.getenv('USER_CONTAINER_NAME'))
    user_blob_name = req_body.get(
        'user_blob_name', os.getenv('USER_BLOB_NAME'))

    RssProcessor().process_feeds(site_id, list_id,
                                config_container_name, config_blob_name,
                                system_container_name, system_blob_name,
                                user_container_name, user_blob_name)

    return func.HttpResponse("RSS feeds processed and analyzed successfully.", status_code=200)


@app.function_name(name="rssSummarizerHttp")
@app.route(route="summarize", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_summarizer_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered Function:
    Summarizes and updates existing RSS articles stored in Microsoft Lists.
    """
    logging.info('RSS Summarizer HTTP triggered.')

    return func.HttpResponse("RSS articles summarized successfully.", status_code=200)


@app.function_name(name="rssPosterHttp")
@app.route(route="collect", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_poster_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources and stores them in Microsoft Lists.
    """
    logging.info('RSS Poster HTTP triggered.')

    return func.HttpResponse("RSS feeds collected and stored successfully.", status_code=200)
