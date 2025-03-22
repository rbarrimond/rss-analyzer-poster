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

import os
import logging

import azure.functions as func
from azure.functions import HttpRequest, HttpResponse

from utils.logger import configure_logging, update_handler_level
from rss_ingestion_service import RssIngestionService

# Configure logging
logger = configure_logging(__name__)

# Create the Azure Functions application instance
app = func.FunctionApp()

@app.function_name(name="rssFeedProcessor")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
def rss_feed_processor(myTimer: func.TimerRequest) -> None:
    """
    Scheduled Azure Function (runs daily at 6 AM UTC):
    Fetches RSS feeds from configured sources and stores them in Microsoft Lists.

    :param myTimer: The timer request object that triggers the function.
    """
    logger.info('RSS Feed Processor triggered.')
    try:
        RssProcessor().read_and_store_feeds()
    except Exception as e:
        logger.error("Error processing RSS feeds: %s", e)

@app.function_name(name="rssFeedProcessorHttp")
@app.route(route="analyze", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_feed_processor_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources, stores them in Microsoft Lists,
    and analyzes each for summaries and scores when invoked externally.

    :param req: The HTTP request object.
    :return: HTTP response indicating the result of the operation.
    """
    logger.info('RSS Feed Processor HTTP triggered.')
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body.", status_code=400)

    config_container_name = req_body.get(
        'config_container_name', os.getenv('CONFIG_CONTAINER_NAME'))
    config_blob_name = req_body.get(
        'config_blob_name', os.getenv('CONFIG_BLOB_NAME'))

    try:
        RssIngestionService().read_and_store_feeds(config_container_name, config_blob_name)
        return func.HttpResponse("RSS feeds processed and analyzed successfully.", status_code=200)
    except Exception as e:
        logger.error(f"Error processing RSS feeds: {e}")
        return func.HttpResponse(f"Error processing RSS feeds: {e}", status_code=500)

@app.function_name(name="rssSummarizerHttp")
@app.route(route="summarize", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_summarizer_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered Function:
    Summarizes and updates existing RSS articles stored in Microsoft Lists.

    :param req: The HTTP request object.
    :return: HTTP response indicating the result of the operation.
    """
    logger.info('RSS Summarizer HTTP triggered.')
    try:
        with lock:  # Ensure atomic access
            # Add the logic to summarize and update existing RSS articles
            pass
        return func.HttpResponse("RSS articles summarized successfully.", status_code=200)
    except Exception as e:
        logger.error(f"Error summarizing RSS articles: {e}")
        return func.HttpResponse(f"Error summarizing RSS articles: {e}", status_code=500)

@app.function_name(name="rssPosterHttp")
@app.route(route="collect", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def rss_poster_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources and stores them in Microsoft Lists.

    :param req: The HTTP request object.
    :return: HTTP response indicating the result of the operation.
    """
    logger.info('RSS Poster HTTP triggered.')
    try:
        with lock:  # Ensure atomic access
            # Add the logic to fetch RSS feeds and store them in Microsoft Lists
            pass
        return func.HttpResponse("RSS feeds collected and stored successfully.", status_code=200)
    except Exception as e:
        logger.error(f"Error collecting RSS feeds: {e}")
        return func.HttpResponse(f"Error collecting RSS feeds: {e}", status_code=500)

@app.function_name(name="updateLogLevel")
@app.route(route="updateLogLevel", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def update_log_level(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered Function:
    Updates the log level of the logger based on the request parameter.

    :param req: The HTTP request object.
    :return: HTTP response indicating the result of the operation.
    """
    logger.info('Update Log Level HTTP triggered.')
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body.", status_code=400)

    new_level = req_body.get('log_level', 'INFO').upper()
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    if new_level in level_mapping:
        update_handler_level(logger, level_mapping[new_level])
        return func.HttpResponse(f"Log level updated to {new_level}.", status_code=200)
    else:
        return func.HttpResponse(f"Invalid log level: {new_level}.", status_code=400)
