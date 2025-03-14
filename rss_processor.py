"""
rss_processor.py

This module defines functions for processing and analyzing RSS feeds.

Key Functions:
1. download_blob_content - Downloads the content of a blob from Azure Blob Storage and returns it as a string.
2. process_and_store_feeds - Processes RSS feeds from a configuration file stored in Azure Blob Storage 
   and stores the entries in Microsoft Lists.
3. analyze_and_update_recent_articles - Analyzes recent articles from Microsoft Lists, summarizes them 
   using Azure OpenAI, and updates the list with the summaries and engagement scores.

Dependencies:
- Uses Azure Blob Storage for storing configuration files and role content.
- Integrates with Microsoft Graph API to interact with Microsoft Lists.
- Utilizes Azure OpenAI for generating summaries and engagement scores.
- Uses feedparser for parsing RSS feeds.

Environment Variables:
- Various environment variables are used for configuration, including Azure Blob Storage endpoints, 
  SharePoint site and list IDs, and Azure Key Vault URL for secrets.

Logging:
- Logging is configured to provide detailed information about the operations performed by each function.
"""

import json
import logging
import os
from typing import Optional

import feedparser
import openai
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph import GraphServiceClient
from msgraph.generated.models.field_value_set import FieldValueSet
from msgraph.generated.sites.item.lists.item.items.items_request_builder import ItemsRequestBuilder
from openai import AzureOpenAI
from azure_clients import download_blob_content

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_MODEL_NAME = os.environ.get('AZURE_OPENAI_MODEL_NAME')
client = AzureOpenAI(azure_endpoint="https://rlb-gpt-1.openai.azure.com/openai/deployments/rlb-gpt-4o-100k/chat/completions?api-version=2025-01-01-preview",
    # credential=AzureKeyCredential("<API_KEY>")
)

def process_and_store_feeds(blob_service_client: BlobServiceClient, graph_service_client: GraphServiceClient,
                            site_id: str, list_id: str, config_container_name: str, config_blob_name: str) -> None:
    """
    Processes RSS feeds from a configuration file stored in Azure Blob Storage and stores the entries 
    in Microsoft Lists.

    :param blob_service_client: The BlobServiceClient instance to interact with Azure Blob Storage.
    :param site_id: The ID of the SharePoint site containing the list.
    :param list_id: The ID of the Microsoft List where entries will be stored.
    :param config_container_name: The name of the container where the configuration blob is stored.
    :param config_blob_name: The name of the configuration blob containing RSS feed URLs.
    """

    # Load feed URLs from configuration file
    feeds_json = download_blob_content(blob_service_client, config_container_name, config_blob_name)
    if feeds_json is None:
        logging.error("Failed to load feed URLs from configuration file.")
        return

    config = json.loads(feeds_json)
    items_to_insert = []

    # Parse and store articles
    for feed_url in config.get('feeds', []):
        logging.info('Processing feed: %s', feed_url)
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            # Prepare data for Microsoft Lists
            item_data = {
                "fields": {
                    "Title": entry.get('title', 'No Title'),
                    "URL": entry.get('link', ''),
                    "Summary": entry.get('summary', ''),
                    "Entry_ID": entry.get('id', ''),
                    "Published_Date": entry.get('published', ''),
                    "Full_Content": entry.get('content', [{}])[0].get('value', ''),
                    "Categories": ', '.join([tag['term'] for tag in entry.get('tags', [])]),
                    "Author": entry.get('author', ''),
                    "Keywords": "",  # Placeholder for keyword extraction
                    "Sentiment": '',  # Placeholder for sentiment analysis
                    "Readability_Score": '',  # Placeholder for readability score
                    "Engagement_Score": '',  # Placeholder for engagement score
                    "Processed": False,
                    "Engagement_Type": '',  # Placeholder for engagement type
                    "Response_Received": False
                }
            }
            items_to_insert.append(item_data)

    # Batch insert items into Microsoft Lists
    if items_to_insert:
        graph_service_client.sites.by_site_id(site_id).lists.by_list_id(list_id).items.post(items=items_to_insert)
        logging.info('Added %d articles.', len(items_to_insert))


def analyze_and_update_recent_articles(graph_service_client: GraphServiceClient, site_id: str, list_id: str,
                                       blob_service_client: BlobServiceClient, system_container_name: str,
                                       system_blob_name: str, user_container_name: str, user_blob_name: str) -> None:
    """
    Analyzes recent articles from Microsoft Lists, summarizes them using Azure OpenAI, and updates the list 
    with the summaries and engagement scores.

    :param client: The GraphClient instance to interact with Microsoft Graph API.
    :param site_id: The ID of the SharePoint site containing the list.
    :param list_id: The ID of the Microsoft List containing articles to analyze.
    :param blob_service_client: The BlobServiceClient instance to interact with Azure Blob Storage.
    :param system_container_name: The name of the container where the system role content blob is stored.
    :param system_blob_name: The name of the blob containing the system role content.
    :param user_container_name: The name of the container where the user role content blob is stored.
    :param user_blob_name: The name of the blob containing the user role content.
    """
    # Load role content from Azure Blob Storage
    system_content = download_blob_content(blob_service_client, system_container_name, system_blob_name)
    if system_content is None:
        logging.error("Failed to load system role content.")
        return

    user_content_template = download_blob_content(blob_service_client, user_container_name, user_blob_name)
    if user_content_template is None:
        logging.error("Failed to load user role content.")
        return

    # Fetch items from Microsoft List with necessary fields only
    try:
        query_params = ItemsRequestBuilder.ItemsRequestBuilderGetQueryParameters(
                            expand=["fields(select=Entry_ID,Summary,Full_Content,Keywords,Categories)"])
        request_configuration = RequestConfiguration(query_parameters=query_params)
        items = graph_service_client.sites.by_site_id(site_id).lists.by_list_id(list_id).items.get(request_configuration=request_configuration)
    except Exception as e:
        logging.error('Failed to fetch items from Microsoft List: %s', e)
        return

    for item in items:
        content_text = item.get('fields', {}).get('summary', '')
        if not content_text:
            logging.info('Skipping item with ID %s due to empty content.', item.get("id"))
            continue

        # Format the user message with the content text
        user_content = user_content_template.format(content_text=content_text)

        # Call Azure OpenAI for chat-based summarization
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_content,
                    },
                    {
                        "role": "user",
                        "content": user_content,
                    }
                ],
                max_tokens=4096,
                temperature=1.0,
                top_p=1.0,
                model="rlb-gpt-4o-100k",
                api_version="2025-01-01-preview",
                timeout=60
            )

            if response.choices:
                content = response.choices[0].message.content.strip()
                parsed_response = json.loads(content)
                summary_text = parsed_response.get("summary", "No summary")
                engagement_score = parsed_response.get("score", 5)
                if not isinstance(engagement_score, int):
                    engagement_score = 5
            else:
                summary_text = "No summary"
                engagement_score = 5
        except openai.OpenAIError as e:
            logging.error('OpenAI API error: %s', e)
            summary_text = "No summary"
            engagement_score = 5
        except (json.JSONDecodeError, TypeError):
            summary_text = "No summary"
            engagement_score = 5

        # Update the item in Microsoft List directly
        request_body = FieldValueSet(additional_data={"analysis_summary": summary_text, "engagement_score": engagement_score})

        result = graph_service_client.sites.by_site_id(site_id).lists.by_list_id(list_id).items.by_list_item_id(item["id"]).fields.patch(request_body)

        logging.info("Updated article %s with status %s.", item.get("id"), result[0])
