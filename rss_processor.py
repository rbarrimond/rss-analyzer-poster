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
import os

import feedparser
import openai
import pandas as pd
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.models.field_value_set import FieldValueSet
from msgraph.generated.sites.item.lists.item.items.items_request_builder import ItemsRequestBuilder
from utils.azure_clients import AzureClientFactory
from utils.logger import configure_logging
from utils.rss_lists import fetch_processed_status, create_output_df, post_feed_entries

# Configure logging
logger = configure_logging(__name__)

class RssProcessor:
    """
    RssProcessor is responsible for processing and analyzing RSS feeds.

    Key Responsibilities:
    - Downloading and parsing RSS feed content from Azure Blob Storage.
    - Storing parsed RSS feed entries into Microsoft Lists.
    - Analyzing recent articles from Microsoft Lists using Azure OpenAI.
    - Updating Microsoft Lists with summaries and engagement scores.

    Dependencies:
    - Azure Blob Storage for storing configuration files and role content.
    - Microsoft Graph API for interacting with Microsoft Lists.
    - Azure OpenAI for generating summaries and engagement scores.
    - feedparser for parsing RSS feeds.
    """

    def __init__(self):
        self.acf = AzureClientFactory.get_instance()
        self.azure_openai_client = None
        self.graph_service_client = None

    async def initialize_clients(self):
        self.azure_openai_client = await self.acf.get_openai_client()
        self.graph_service_client = await self.acf.get_graph_client()

    async def process_feeds(self, site_id: str = None, list_id: str = None, 
                            config_container_name: str = None, config_blob_name: str = None, 
                            system_container_name: str = None, system_blob_name: str = None, 
                            user_container_name: str = None, user_blob_name: str = None) -> None:
        """
        Processes RSS feeds and analyzes them.

        :param site_id: The SharePoint site ID. Defaults to environment variable if not provided.
        :param list_id: The Microsoft List ID. Defaults to environment variable if not provided.
        :param config_container_name: The name of the container where the configuration blob is stored. 
                                      Defaults to environment variable if not provided.
        :param config_blob_name: The name of the configuration blob. Defaults to environment variable if not provided.
        :param system_container_name: The name of the container where the system role content blob is stored. 
                                      Defaults to environment variable if not provided.
        :param system_blob_name: The name of the blob containing the system role content. Defaults to environment variable if not provided.
        :param user_container_name: The name of the container where the user role content blob is stored. 
                                    Defaults to environment variable if not provided.
        :param user_blob_name: The name of the blob containing the user role content. Defaults to environment variable if not provided.
        """
        await self.initialize_clients()
        await self.read_and_store_feeds(site_id, list_id, config_container_name, config_blob_name)
        await self.analyze_and_update_recent_articles(site_id, list_id, system_container_name, system_blob_name, user_container_name, user_blob_name)

    async def read_and_store_feeds(self, site_id: str = None, list_id: str = None, 
                                   config_container_name: str = None, config_blob_name: str = None) -> None:
        """
        Reads and stores RSS feeds.

        :param site_id: The SharePoint site ID. Defaults to environment variable if not provided.
        :param list_id: The Microsoft List ID. Defaults to environment variable if not provided.
        :param config_container_name: The name of the container where the configuration blob is stored. 
                                      Defaults to environment variable if not provided.
        :param config_blob_name: The name of the configuration blob. Defaults to environment variable if not provided.
        """
        # Configure this object with the necessary clients and parameters
        await self.initialize_clients()
        site_id, list_id, config_container_name, config_blob_name = self._get_config_params(
            site_id, list_id, config_container_name, config_blob_name)
        if not all([site_id, list_id, config_container_name, config_blob_name]):
            raise ValueError("Missing required parameters for reading and storing feeds.")

        # Download the configuration file containing feed URLs
        feeds_json = await self.acf.download_blob_content(config_container_name, config_blob_name)
        if feeds_json is None:
            logger.error("Failed to load feed URLs from configuration file.")
            return
        config = json.loads(feeds_json)

        # Fetch the status of items already processed from Microsoft List
        items_status = await fetch_processed_status(self.graph_service_client, site_id, list_id)
        if items_status is None:
            logger.warning("No items status fetched from Microsoft List.")
            return

        # Process each feed URL from the configuration
        for feed_url in config.get('feeds', []):
            logger.info('Processing feed: %s', feed_url)
            try:
                feed = feedparser.parse(feed_url)
                if feed.entries:
                    fp_df = pd.DataFrame(feed.entries)
                    if 'id' in fp_df.columns:
                        fp_df.set_index('id', inplace=True)
                        # Reindex items_status to match fp_df index
                        items_status = items_status.reindex(fp_df.index, fill_value=False)
                        # Create filtered output DataFrame by excluding already processed entries
                        output_df = create_output_df(fp_df[~items_status])
                        await post_feed_entries(self.graph_service_client, output_df, site_id, list_id)
                    else:
                        logger.warning('Feed entries do not contain an "id" field: %s', feed_url)
            except Exception as e:
                logger.warning('Failed to process feed %s: %s', feed_url, e)

    def _get_config_params(self, site_id: str, list_id: str, config_container_name: str, config_blob_name: str):
        site_id = site_id or os.getenv('SITE_ID')
        list_id = list_id or os.getenv('LIST_ID')
        config_container_name = config_container_name or os.getenv('CONFIG_CONTAINER_NAME')
        config_blob_name = config_blob_name or os.getenv('CONFIG_BLOB_NAME')
        return site_id, list_id, config_container_name, config_blob_name

    async def analyze_and_update_recent_articles(self, site_id: str = None, list_id: str = None, 
                                                 system_container_name: str = None, system_blob_name: str = None, 
                                                 user_container_name: str = None, user_blob_name: str = None) -> None:
        """
        Analyzes recent articles from Microsoft Lists, summarizes them using Azure OpenAI, and updates the list 
        with the summaries and engagement scores.

        :param site_id: The ID of the SharePoint site containing the list. Defaults to environment variable if not provided.
        :param list_id: The ID of the Microsoft List containing articles to analyze. Defaults to environment variable if not provided.
        :param system_container_name: The name of the container where the system role content blob is stored. 
                                      Defaults to environment variable if not provided.
        :param system_blob_name: The name of the blob containing the system role content. Defaults to environment variable if not provided.
        :param user_container_name: The name of the container where the user role content blob is stored. 
                                    Defaults to environment variable if not provided.
        :param user_blob_name: The name of the blob containing the user role content. Defaults to environment variable if not provided.
        """
        site_id = site_id or os.getenv('SITE_ID')
        list_id = list_id or os.getenv('LIST_ID')
        system_container_name = system_container_name or os.getenv('SYSTEM_CONTAINER_NAME')
        system_blob_name = system_blob_name or os.getenv('SYSTEM_BLOB_NAME')
        user_container_name = user_container_name or os.getenv('USER_CONTAINER_NAME')
        user_blob_name = user_blob_name or os.getenv('USER_BLOB_NAME')

        if not all([site_id, list_id, system_container_name, system_blob_name, user_container_name, user_blob_name]):
            raise ValueError("Missing required parameters for analyzing and updating recent articles.")

        # Load role content from Azure Blob Storage
        system_content = await self.acf.download_blob_content(system_container_name, system_blob_name)
        if system_content is None:
            logger.error("Failed to load system role content.")
            return

        user_content_template = await self.acf.download_blob_content(user_container_name, user_blob_name)
        if user_content_template is None:
            logger.error("Failed to load user role content.")
            return

        # Fetch items from Microsoft List with necessary fields only
        try:
            query_params = ItemsRequestBuilder.ItemsRequestBuilderGetQueryParameters(
                                expand=["fields(select=Entry_ID,Summary,Full_Content,Keywords,Categories)"])
            request_configuration = RequestConfiguration(query_parameters=query_params)
            items = await self.graph_service_client.sites[site_id].lists[list_id].items.get(request_configuration=request_configuration)
        except Exception as e:
            logger.error('Failed to fetch items from Microsoft List: %s', e)
            return

        for item in items:
            content_text = item.get('fields', {}).get('summary', '')
            if not content_text:
                logger.info('Skipping item with ID %s due to empty content.', item.get("id"))
                continue

            # Format the user message with the content text
            user_content = user_content_template.format(content_text=content_text)

            # Call Azure OpenAI for chat-based summarization
            try:
                response = await self.azure_openai_client.chat.completions.create(
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
                logger.error('OpenAI API error: %s', e)
                summary_text = "No summary"
                engagement_score = 5
            except (json.JSONDecodeError, TypeError):
                summary_text = "No summary"
                engagement_score = 5

            # Update the item in Microsoft List directly
            request_body = FieldValueSet(additional_data={"analysis_summary": summary_text, "engagement_score": engagement_score})

            result = await self.graph_service_client.sites.by_site_id(site_id).lists.by_list_id(list_id).items.by_list_item_id(item["id"]).fields.patch(request_body)

            logger.info("Updated article %s with status %s.", item.get("id"), result[0])
