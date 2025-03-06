import json
import logging
import os
from typing import Any
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser  # Ensure feedparser is imported
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# If needed, install and import openai:
# pip install openai
import openai

def process_and_store_feeds(azure_storageaccount_blobendpoint: str, 
                            cosmos_db_endpoint: str, 
                            cosmos_db_name: str, 
                            cosmos_db_container: str,
                            config_container_name: str = "config",
                            config_blob_name: str = "feeds.json") -> None:
    """
    Fetches RSS feed URLs from blob storage, parses them, and saves RSS entries in Cosmos DB.
    """
    logging.info('Processing RSS feeds.')

    # Connect to Azure Blob Storage and Cosmos DB via managed identity
    blob_service_client = BlobServiceClient(
        account_url=azure_storageaccount_blobendpoint,
        credential=DefaultAzureCredential()
    )
    cosmos_client = CosmosClient(
        url=cosmos_db_endpoint,
        credential=DefaultAzureCredential()
    )
    database = cosmos_client.get_database_client(cosmos_db_name)
    container = database.get_container_client(cosmos_db_container)

    # Load feed URLs from configuration file
    config_container_client = blob_service_client.get_container_client(config_container_name)
    blob_client = config_container_client.get_blob_client(config_blob_name)
    feeds_json = blob_client.download_blob().readall()
    config = json.loads(feeds_json)

    # Parse and store articles
    for feed_url in config.get('feeds', []):
        logging.info('Processing feed: %s', feed_url)
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            container.upsert_item(entry)


def analyze_and_update_recent_articles(cosmos_db_endpoint: str,
                                       cosmos_db_name: str,
                                       cosmos_db_container: str,
                                       threshold_days: int = 7) -> None:
    """
    Summarizes recent articles and assigns an engagement score using Azure OpenAI. Only articles
    published within 'threshold_days' are processed, and items already analyzed are skipped.
    """
    logging.info('Analyzing recent articles with Azure OpenAI.')

    # Configure Azure OpenAI
    openai.api_type = "azure"
    openai.api_key = os.getenv("AZURE_OPENAI_KEY", "")
    openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    openai.api_version = "2023-03-15-preview"
    azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "my-deployment")

    # Connect to Cosmos DB container
    cosmos_client = CosmosClient(
        url=cosmos_db_endpoint,
        credential=DefaultAzureCredential()
    )
    database = cosmos_client.get_database_client(cosmos_db_name)
    container = database.get_container_client(cosmos_db_container)

    # Filter out items based on date threshold
    cutoff_date = datetime.now(datetime.timezone.utc) - timedelta(days=threshold_days)
    items = list(container.read_all_items(max_item_count=100))

    for item in items:
        try:
            # Skip articles if they're already summarized or scored
            if "analysis_summary" in item or "engagement_score" in item:
                continue

            # Only proceed if the "published" date is valid and recent
            published_str = item.get('published')
            if not published_str:
                continue
            published_dt = parsedate_to_datetime(published_str)
            if published_dt < cutoff_date:
                continue

            # Retrieve the relevant body text for summarization
            content_text = ""
            if 'content' in item and isinstance(item['content'], list) and item['content']:
                content_text = item['content'][0].get('value', '')
            else:
                content_text = item.get('summary', '')

            if not content_text:
                continue

            prompt_text = (
                "Summarize the following text and provide a numerical engagement score (1-10) "
                f"based on how interesting it might be:\n\n{content_text}\n\n"
                "Respond in JSON format with keys: summary, score."
            )

            # Call Azure OpenAI for chat-based summarization
            response = openai.ChatCompletion.create(
                engine=azure_openai_deployment,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.7,
                max_tokens=150
            )

            # Parse the response, ensuring it includes a valid summary and score
            try:
                content = response.choices[0].message.content.strip()
                parsed_response = json.loads(content)
                summary_text = parsed_response.get("summary", "No summary")
                engagement_score = parsed_response.get("score", 5)
                if not isinstance(engagement_score, int):
                    engagement_score = 5
            except (json.JSONDecodeError, TypeError):
                summary_text = "No summary"
                engagement_score = 5

            # Update the item in Cosmos DB
            item["analysis_summary"] = summary_text
            item["engagement_score"] = engagement_score
            container.upsert_item(item)
            logging.info("Azure OpenAI summary/score added to article %s.", item.get("id"))

        except (openai.error.OpenAIError, KeyError) as e:
            logging.error("Error processing item %s: %s", item.get("id"), e)