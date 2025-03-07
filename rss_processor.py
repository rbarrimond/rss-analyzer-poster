import json
import logging
import os
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser  # Third-party library for parsing RSS feeds
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from msal import ConfidentialClientApplication
from msgraph.core import GraphClient
import openai  # For calling the OpenAI API

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',  # Define the log message format
    datefmt='%Y-%m-%d %H:%M:%S'  # Define the date format
)

# Global constants initialized by environment variables
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')

def process_and_store_feeds(azure_storageaccount_blobendpoint: str,
                            site_id: str,
                            list_id: str,
                            config_container_name: str = "config",
                            config_blob_name: str = "feeds.json") -> None:
    """
    Fetches RSS feed URLs from blob storage, parses them, and saves RSS entries in Microsoft Lists.
    """
    logging.info('Processing RSS feeds.')

    # Connect to Azure Blob Storage via managed identity
    blob_service_client = BlobServiceClient(
        account_url=azure_storageaccount_blobendpoint,
        credential=DefaultAzureCredential()
    )

    # Initialize Microsoft Graph client
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    client = GraphClient(credential=token['access_token'])

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
            # Prepare data for Microsoft Lists
            item_data = {
                "fields": {
                    "Title": entry.get('title', 'No Title'),
                    "Link": entry.get('link', ''),
                    "Published": entry.get('published', ''),
                    "Summary": entry.get('summary', '')
                }
            }
            # Insert item into Microsoft Lists
            client.post(f'/sites/{site_id}/lists/{list_id}/items', json=item_data)

def update_item_in_list(client, list_id, item_id, summary_text, engagement_score):
    update_data = {
        "fields": {
            "analysis_summary": summary_text,
            "engagement_score": engagement_score
        }
    }
    client.patch(
        f'/sites/YOUR_SITE_ID/lists/{list_id}/items/{item_id}', json=update_data)


def analyze_and_update_recent_articles(client):
    # Fetch items from Microsoft List
    response = client.get(f'/sites/YOUR_SITE_ID/lists/YOUR_LIST_ID/items')
    items = response.json().get('value', [])

    for item in items:
        content_text = item.get('fields', {}).get('summary', '')
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

        # Parse the response
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

        # Update the item in Microsoft List
        update_item_in_list(client, 'YOUR_LIST_ID',
                            item['id'], summary_text, engagement_score)
        logging.info(
            "Azure OpenAI summary/score added to article %s.", item.get("id"))
