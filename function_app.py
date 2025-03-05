import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func
import feedparser
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

@app.function_name(name="rssFeedDownloader")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
def rssFeedDownloader(myTimer: func.TimerRequest) -> None:
    """
    Downloads RSS feeds and stores them in Azure Cosmos DB.
    """
    logging.info('RSS Feed Downloader triggered.')
    process_feeds()

@app.function_name(name="rssFeedDownloaderHttp")
@app.route(route="download", methods=["POST"])
def rssFeedDownloaderHttp(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to download RSS feeds.
    """
    process_feeds()
    return func.HttpResponse("RSS feeds downloaded and stored successfully.", status_code=200)

def process_feeds():
    """
    Downloads RSS feeds and stores them in Azure Cosmos DB.
    """
    logging.info('Processing RSS feeds.')

    # Retrieve environment variables
    azure_storageaccount_blobendpoint = os.getenv('AZURE_STORAGEACCOUNT_BLOBENDPOINT')
    cosmos_db_endpoint = os.getenv('AZURE_COSMOS_DB_ENDPOINT')
    cosmos_db_name = os.getenv('AZURE_COSMOS_DB_NAME')
    cosmos_db_container = os.getenv('AZURE_COSMOS_DB_CONTAINER')

    # Connect to Azure Blob Storage using managed identity
    blob_service_client = BlobServiceClient(account_url=azure_storageaccount_blobendpoint,
                                            credential=DefaultAzureCredential())

    # Connect to Azure Cosmos DB using managed identity
    cosmos_client = CosmosClient(url=cosmos_db_endpoint, 
                                 credential=DefaultAzureCredential())
    database = cosmos_client.get_database_client(cosmos_db_name)
    container = database.get_container_client(cosmos_db_container)

    # Load feed URLs from configuration file
    config_container_client = blob_service_client.get_container_client('config')
    blob_client = config_container_client.get_blob_client('feeds.json')
    feeds_json = blob_client.download_blob().readall()
    config = json.loads(feeds_json)

    # List of RSS feed URLs to be processed
    feed_urls = config['feeds']

    # Iterate over each feed URL to download and process the RSS feed
    for feed_url in feed_urls:
        # Parse the RSS feed using feedparser
        feed = feedparser.parse(feed_url)
        # Iterate over each entry in the feed
        for entry in feed.entries:
            # Create a dictionary to store article data
            article_data = {
                'id': entry.id,  # Unique identifier for the article
                'title': entry.title,  # Title of the article
                'link': entry.link,  # URL link to the full article
                'summary': entry.summary,  # Summary or description of the article
                'published': entry.published  # Publication date of the article
            }
            # Upsert the article data into the Azure Cosmos DB container
            container.upsert_item(article_data)

    # Log a message indicating successful download and storage of RSS feeds
    logging.info("RSS feeds downloaded and stored in Cosmos DB successfully.")

@app.function_name(name="contentSummarizer")
@app.route(route="summarize", methods=["POST"])
def contentSummarizer(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to summarize content.
    This function serves as a placeholder for content summarization logic.
    It is triggered via an HTTP POST request to the /summarize route.
    """
    logging.info('Content Summarizer triggered.')
    # Placeholder logic for content summarization
    return func.HttpResponse("Content summarization completed.", status_code=200)

@app.function_name(name="contentRanker")
@app.route(route="rank", methods=["POST"])
def contentRanker(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to rank content.
    This function serves as a placeholder for content ranking logic.
    It is triggered via an HTTP POST request to the /rank route.
    """
    logging.info('Content Ranker triggered.')
    # Placeholder logic for content ranking
    return func.HttpResponse("Content ranking completed.", status_code=200)

@app.function_name(name="linkedinPostSuggester")
@app.route(route="suggest", methods=["POST"])
def linkedinPostSuggester(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered function to suggest LinkedIn posts.
    This function serves as a placeholder for LinkedIn post suggestion logic.
    It is triggered via an HTTP POST request to the /suggest route.
    """
    logging.info('LinkedIn Post Suggester triggered.')
    # Placeholder logic for LinkedIn post suggestion
    return func.HttpResponse("LinkedIn post suggestion completed.", status_code=200)

