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
    Scheduled function to analyze and post RSS feeds.
    """
    logging.info('RSS Analyzer Poster triggered.')
    process_and_store_feeds(AZURE_STORAGEACCOUNT_BLOBENDPOINT,
                            AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_NAME, AZURE_COSMOS_DB_CONTAINER)
    analyze_and_update_recent_articles(
        AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_NAME, AZURE_COSMOS_DB_CONTAINER)


@app.function_name(name="rssAnalyzerPosterHttp")
@app.route(route="analyze", methods=["POST"])
def rssAnalyzerPosterHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to analyze and post RSS feeds.
    """
    process_and_store_feeds(AZURE_STORAGEACCOUNT_BLOBENDPOINT,
                            AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_NAME, AZURE_COSMOS_DB_CONTAINER)
    analyze_and_update_recent_articles(
        AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_NAME, AZURE_COSMOS_DB_CONTAINER)
    return func.HttpResponse("RSS feeds have been successfully analyzed and updated.", status_code=200)

@app.function_name(name="rssSummarizerHttp")
@app.route(route="summarize", methods=["POST"])
def rssSummarizerHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to summarize and score RSS articles.
    """
    analyze_and_update_recent_articles(AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_NAME, AZURE_COSMOS_DB_CONTAINER)
    return func.HttpResponse("RSS articles summarized successfully.", status_code=200)

@app.function_name(name="rssPosterHttp")
@app.route(route="collect", methods=["POST"])
def rssPosterHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to fetch RSS feeds and store them in Cosmos DB.
    """
    process_and_store_feeds(AZURE_STORAGEACCOUNT_BLOBENDPOINT,
                            AZURE_COSMOS_DB_ENDPOINT, AZURE_COSMOS_DB_NAME,
                            AZURE_COSMOS_DB_CONTAINER)
    return func.HttpResponse("RSS feeds collected and stored successfully.", status_code=200)
