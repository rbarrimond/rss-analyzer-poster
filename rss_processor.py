import json
import logging
import os
from azure.storage.blob import BlobServiceClient
from msgraph import GraphServiceClient
import openai
import feedparser
from graph import get_graph_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def download_blob_content(blob_service_client: BlobServiceClient, container_name: str, blob_name: str) -> str:
    """
    Downloads the content of a blob from Azure Blob Storage and returns it as a string.

    :param blob_service_client: The BlobServiceClient instance to interact with Azure Blob Storage.
    :param container_name: The name of the container where the blob is stored.
    :param blob_name: The name of the blob to download.
    :return: The content of the blob as a string.
    """
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    blob_data = blob_client.download_blob().readall()
    return blob_data.decode('utf-8').strip()


def process_and_store_feeds(blob_service_client: BlobServiceClient, site_id: str, list_id: str,
                            config_container_name: str, config_blob_name: str) -> None:
    """
    Processes RSS feeds from a configuration file stored in Azure Blob Storage and stores the entries 
    in Microsoft Lists.

    :param blob_service_client: The BlobServiceClient instance to interact with Azure Blob Storage.
    :param site_id: The ID of the SharePoint site containing the list.
    :param list_id: The ID of the Microsoft List where entries will be stored.
    :param config_container_name: The name of the container where the configuration blob is stored.
    :param config_blob_name: The name of the configuration blob containing RSS feed URLs.
    """
    client = get_graph_client()

    # Load feed URLs from configuration file
    feeds_json = download_blob_content(
        blob_service_client, config_container_name, config_blob_name)
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
                    "Link": entry.get('link', ''),
                    "Published": entry.get('published', ''),
                    "Summary": entry.get('summary', '')
                }
            }
            items_to_insert.append(item_data)

    # Batch insert items into Microsoft Lists
    if items_to_insert:
        client.post(
            f'/sites/{site_id}/lists/{list_id}/items', json={"value": items_to_insert})
        logging.info('Added %d articles.', len(items_to_insert))


def analyze_and_update_recent_articles(client: GraphServiceClient, site_id: str, list_id: str,
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
    system_content = download_blob_content(
        blob_service_client, system_container_name, system_blob_name)
    user_content_template = download_blob_content(
        blob_service_client, user_container_name, user_blob_name)

    # Fetch items from Microsoft List with necessary fields only
    try:
        response = client.get(f'/sites/{site_id}/lists/{list_id}/items?$select=id,fields')
        items = response.json().get('value', [])
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
            response = openai.ChatCompletion.create(
                engine=os.getenv('AZURE_OPENAI_DEPLOYMENT'),
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_tokens=150
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
        except openai.error.OpenAIError as e:
            logging.error('OpenAI API error: %s', e)
            summary_text = "No summary"
            engagement_score = 5
        except (json.JSONDecodeError, TypeError):
            summary_text = "No summary"
            engagement_score = 5

        # Update the item in Microsoft List directly
        update_data = {
            "fields": {
                "analysis_summary": summary_text,
                "engagement_score": engagement_score
            }
        }
        update_response = client.patch(
            f'/sites/{site_id}/lists/{list_id}/items/{item["id"]}', json=update_data)
        logging.info("Updated article %s with status %s.", item.get("id"), update_response.status_code)
