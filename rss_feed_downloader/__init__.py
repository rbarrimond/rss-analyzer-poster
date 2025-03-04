import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func
import feedparser
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

def main(myTimer: func.TimerRequest) -> None:
    logging.info('RSS Feed Downloader triggered.')

    # Retrieve environment variables
    storage_account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
    cosmos_db_endpoint = os.getenv('AZURE_COSMOS_DB_ENDPOINT')
    cosmos_db_name = os.getenv('AZURE_COSMOS_DB_NAME')
    cosmos_db_container = os.getenv('AZURE_COSMOS_DB_CONTAINER')

    # Connect to Azure Blob Storage using managed identity
    blob_service_client = BlobServiceClient(account_url=storage_account_url, 
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
    feed_urls = config['feeds']

    # Process each feed URL
    for feed_url in feed_urls:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            # Prepare the data to be stored
            article_data = {
                'id': entry.id,
                'title': entry.title,
                'link': entry.link,
                'summary': entry.summary,
                'published': entry.published,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Insert the article data into Cosmos DB
            container.upsert_item(article_data)

    logging.info("RSS feeds downloaded and stored in Cosmos DB successfully.")
