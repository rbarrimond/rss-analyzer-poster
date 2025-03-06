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
    Processes RSS feeds and stores them in Azure Cosmos DB.
    """
    logging.info('Processing RSS feeds.')

    # Connect to Azure Blob Storage using managed identity
    blob_service_client = BlobServiceClient(
        account_url=azure_storageaccount_blobendpoint,
        credential=DefaultAzureCredential()
    )

    # Connect to Azure Cosmos DB using managed identity
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

    # Process each feed URL
    for feed_url in config.get('feeds', []):
        logging.info('Processing feed: %s', feed_url)
        feed = feedparser.parse(feed_url)
        # Store feed entries in Cosmos DB
        for entry in feed.entries:
            container.upsert_item(entry)


def analyze_and_update_recent_articles(cosmos_db_endpoint: str,
                                       cosmos_db_name: str,
                                       cosmos_db_container: str,
                                       threshold_days: int = 7) -> None:
    """
    Reads articles published within the last 'threshold_days', sends them to OpenAI for
    summarization and scoring, then updates each article in the Cosmos DB container.
    Skips articles that already have 'analysis_summary' or 'engagement_score'.
    """
    logging.info('Analyzing recent articles with OpenAI.')

    # Set your OpenAI API key from environment variable
    openai.api_key = os.getenv("OPENAI_API_KEY", "")

    # Connect to Azure Cosmos DB using managed identity
    cosmos_client = CosmosClient(
        url=cosmos_db_endpoint,
        credential=DefaultAzureCredential()
    )
    database = cosmos_client.get_database_client(cosmos_db_name)
    container = database.get_container_client(cosmos_db_container)

    # Define the date threshold
    cutoff_date = datetime.utcnow() - timedelta(days=threshold_days)

    # Read recent items
    items = list(container.read_all_items(max_item_count=100))

    for item in items:
        try:
            # Skip items if they've already been analyzed
            if "analysis_summary" in item or "engagement_score" in item:
                continue

            published_str = item.get('published')
            if not published_str:
                continue

            published_dt = parsedate_to_datetime(published_str)
            if published_dt < cutoff_date:
                continue

            # Get original text
            content_text = ""
            if 'content' in item and isinstance(item['content'], list) and item['content']:
                content_text = item['content'][0].get('value', '')
            else:
                content_text = item.get('summary', '')

            if not content_text:
                continue

            # Prompt OpenAI for summary and score
            prompt_text = (
                "Summarize the following text and provide a numerical engagement score (1-10) "
                f"based on how interesting it might be:\n\n{content_text}\n\n"
                "Respond in JSON format with keys: summary, score."
            )

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.7,
                max_tokens=150
            )

            # Extract summary and score from OpenAI response
            try:
                content = response.choices[0].message.content.strip()
                # Expecting JSON such as: {"summary": "...", "score": 7}
                parsed_response = json.loads(content)
                summary_text = parsed_response.get("summary", "")
                engagement_score = parsed_response.get("score", 5)
            except json.JSONDecodeError:
                # Fallback if response is not valid JSON
                summary_text = "No summary"
                engagement_score = 5

            # Update the article
            item["analysis_summary"] = summary_text
            item["engagement_score"] = engagement_score

            container.upsert_item(item)
            logging.info("OpenAI summary/score added to article %s.", item.get("id"))
        except Exception as e:
            logging.error("Error processing item %s: %s", item.get("id"), e)