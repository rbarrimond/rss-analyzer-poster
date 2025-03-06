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

import logging
import os

import azure.functions as func
from rss_processor import process_and_store_feeds, analyze_and_update_recent_articles

app = func.FunctionApp()

# Retrieve environment variables
AZURE_STORAGEACCOUNT_BLOBENDPOINT = os.getenv('AZURE_STORAGEACCOUNT_BLOBENDPOINT')
AZURE_COSMOS_DB_ENDPOINT = os.getenv('AZURE_COSMOS_DB_ENDPOINT')
AZURE_COSMOS_DB_NAME = os.getenv('AZURE_COSMOS_DB_NAME')
AZURE_COSMOS_DB_CONTAINER = os.getenv('AZURE_COSMOS_DB_CONTAINER')

@app.function_name(name="rssAnalyzerPoster")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
def rssAnalyzerPoster(myTimer: func.TimerRequest) -> None:
    """
    Scheduled Azure Function (runs daily at 6 AM UTC):

    1. Fetches RSS feeds from configured sources and stores them in Cosmos DB.
    2. Analyzes newly stored content with Azure OpenAI, generating summaries and scores.
    """
    logging.info('RSS Analyzer Poster triggered.')
    process_and_store_feeds(
        AZURE_STORAGEACCOUNT_BLOBENDPOINT,
        AZURE_COSMOS_DB_ENDPOINT,
        AZURE_COSMOS_DB_NAME,
        AZURE_COSMOS_DB_CONTAINER
    )
    analyze_and_update_recent_articles(
        AZURE_COSMOS_DB_ENDPOINT,
        AZURE_COSMOS_DB_NAME,
        AZURE_COSMOS_DB_CONTAINER
    )

@app.function_name(name="rssAnalyzerPosterHttp")
@app.route(route="analyze", methods=["POST"])
def rssAnalyzerPosterHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources, stores them in Cosmos DB, and
    analyzes each for summaries and scores when invoked externally.
    """
    process_and_store_feeds(
        AZURE_STORAGEACCOUNT_BLOBENDPOINT,
        AZURE_COSMOS_DB_ENDPOINT,
        AZURE_COSMOS_DB_NAME,
        AZURE_COSMOS_DB_CONTAINER
    )
    analyze_and_update_recent_articles(
        AZURE_COSMOS_DB_ENDPOINT,
        AZURE_COSMOS_DB_NAME,
        AZURE_COSMOS_DB_CONTAINER
    )
    return func.HttpResponse("RSS feeds have been successfully analyzed and updated.", status_code=200)

@app.function_name(name="rssSummarizerHttp")
@app.route(route="summarize", methods=["POST"])
def rssSummarizerHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Function:
    Summarizes and updates existing RSS articles stored in Cosmos DB.
    """
    analyze_and_update_recent_articles(
        AZURE_COSMOS_DB_ENDPOINT,
        AZURE_COSMOS_DB_NAME,
        AZURE_COSMOS_DB_CONTAINER
    )
    return func.HttpResponse("RSS articles summarized successfully.", status_code=200)

@app.function_name(name="rssPosterHttp")
@app.route(route="collect", methods=["POST"])
def rssPosterHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Function:
    Fetches RSS feeds from configured sources and stores them in Cosmos DB 
    without summarizing or scoring.
    """
    process_and_store_feeds(
        AZURE_STORAGEACCOUNT_BLOBENDPOINT,
        AZURE_COSMOS_DB_ENDPOINT,
        AZURE_COSMOS_DB_NAME,
        AZURE_COSMOS_DB_CONTAINER
    )
    return func.HttpResponse("RSS feeds collected and stored successfully.", status_code=200)
