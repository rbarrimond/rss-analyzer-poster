"""
rss_ingestion_service.py

This module defines functions for processing and analyzing RSS feeds.

Key Functions:
1. download_blob_content - Downloads the content of a blob from Azure Blob Storage and returns it as a string.
2. read_and_store_feeds - Processes RSS feeds from a configuration file stored in Azure Blob Storage, enriches them with AI, 
   and stores the entries in Azure Table Storage.
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
from typing import Tuple

import feedparser
import pandas as pd
import xxhash
from azure.ai.inference import ChatCompletionsClient

from utils.azclients import AzureClientFactory as acf
from utils.decorators import (log_and_raise_error, log_execution_time,
                              trace_class)
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)

class AIEnrichmentService:
    """
    Service for AI-driven enrichment of RSS feed data.
    """
    def __init__(self):
        """
        Initializes the AIEnrichmentService and sets up the AzureClientFactory.
        """
        self.acf = acf.get_instance()
        self.openai_clients = self.acf.openai_clients
        self.table_service_client = self.acf.table_service_client

    def enrich_data(self, data: dict) -> dict:
        """
        Enriches RSS feed data using Azure OpenAI models.

        :param data: The RSS feed data to enrich.
        :return: The enriched data.
        """
        logger.info("Enriching data using OpenAI models.")
        # Example usage of OpenAI clients
        model_client = self.openai_clients.get("MODEL_SUMMARY")
        if not model_client:
            raise ValueError("OpenAI client for MODEL_SUMMARY is not configured.")
        # ...existing enrichment logic...
        return data

    @log_and_raise_error("Failed to read and store RSS feeds.")
    def read_and_store_feeds(self, config_container_name: str = os.getenv('CONFIG_CONTAINER_NAME'),
                             config_blob_name: str = os.getenv('CONFIG_BLOB_NAME')) -> None:
        """
        Reads RSS feeds, enriches them with AI, stores results in Azure Table Storage.

        :param config_container_name: Name of the Azure Blob Storage container holding the configuration file.
        :param config_blob_name: Name of the blob within the container that contains the configuration file.
        :raises ValueError: If required configuration parameters are missing or clients fail to initialize.
        :raises RuntimeError: If the configuration file fails to load.
        """

        table_client = self.acf.get_table_service_client()
        openai_client = self.acf.get_openai_clients()["MODEL_RANKING"]
        feed_urls = self._retrieve_feed_urls(config_container_name, config_blob_name)
        
        logger.info("Retrieving feeds from URLs: %s", feed_urls)
        for feed_url in feed_urls:
            fp_enriched_df = self._retrieve_feed(feed_url)


        # AI Enrichment
        # try:
        #     fp_enriched_df["Summary"] = fp_enriched_df["Summary"].apply(lambda text: self._improve_summary(text, openai_client))
        #     fp_enriched_df[["Sentiment", "Sentiment_Score"]] = fp_enriched_df["Summary"].apply(lambda text: pd.Series(self._analyze_sentiment(text, openai_client)))
        #     fp_enriched_df["readability"] = fp_enriched_df["Summary"].apply(lambda text: self._compute_readability(text))
        #     fp_enriched_df["embedding"] = fp_enriched_df["Summary"].apply(lambda text: self._generate_embedding(text, openai_client))
        #     logger.info("Successfully enriched entries for feed: %s", feed_url)
        # except Exception as e:
        #     logger.error("Failed to enrich entries: %s", e)

        # Store in Azure Table Storage
        self._store_in_table_storage(table_client, fp_enriched_df)

    @log_and_raise_error("Failed to retrieve RSS feeds.")
    def _retrieve_feed(self, feed_url: str) -> pd.DataFrame:
        """
        Retrieves RSS feeds from the provided URLs.

        :param feed_urls: List of URLs for RSS feeds.
        :return: DataFrame containing the parsed feed entries.
        """
        feed = feedparser.parse(feed_url)
        logger.info('Processing feed: %s at URL: %s', feed.title, feed_url)
        if feed.entries:
            fp_df = pd.DataFrame(feed.entries)
            if 'id' in fp_df.columns:
                fp_df.set_index('id', inplace=True)
                return self._create_feed_output_df(fp_df)
            else:
                logger.warning('Feed entries do not contain an "id" field: %s', feed_url)
        else:
            logger.warning('No entries found in feed: %s', feed_url)
        
        return pd.DataFrame()

    @log_execution_time()
    @log_and_raise_error("Failed to retrieve feed URLs from config.")
    def _retrieve_feed_urls(self, config_container_name: str, config_blob_name: str) -> list:
        if not all([config_container_name, config_blob_name]):
            logger.error("Missing required config parameters. container=%s, blob=%s", config_container_name, config_blob_name)
            raise ValueError("Missing required config parameters.")

        feed_urls = json.loads(self.acf.download_blob_content(config_container_name, config_blob_name)).get("feeds", [])

        if not feed_urls:
            raise ValueError("No feed URLs found in the configuration file.")
        
        return feed_urls
        
    def _create_feed_output_df(self, input_df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates an output DataFrame with predefined columns from the input DataFrame.

        :param input_df: Input DataFrame containing RSS feed entries from feedparser.
        :return: Output DataFrame with specific columns for storing in Microsoft Lists.
        :raises ValueError: If required columns are missing in the input DataFrame.
        """

        required_columns = ["title", "link"]
        missing_columns = [col for col in required_columns if col not in input_df.columns]
        if missing_columns:
            logger.error("Missing required columns in input DataFrame: %s", missing_columns)
            raise ValueError("Missing required columns in input DataFrame.")

        try:
            # Create DataFrame with actual data where available, otherwise use default values
            output_df = pd.DataFrame({
                "Title": input_df["title"],
                "URL": input_df["link"],
                "Summary": input_df["summary"] if "summary" in input_df.columns else "No Summary Available",
                "Entry_ID": input_df.index.map(lambda x: xxhash.xxh64(str(x)).hexdigest()),
                "Published_Date": input_df["published"] if "published" in input_df.columns else "1970-01-01T00:00:00Z",
                "Full_Content": self._extract_full_content(input_df),
                "Categories": self._extract_categories(input_df),
                "Author": input_df["author"] if "author" in input_df.columns else "Unknown Author",
                "Embeddings": [[]], # Embedding vector for topic classification
                "Sentiment": "Neutral", # Positive, Negative, Neutral, Mixed
                "Sentiment_Score": 0.0, # Sentiment score between -1 and 1
                "Readability_FK": 0.0, # Flesch-Kincaid Readability Score
                "Readability_DC": 0.0, # Dale-Chall Readability Score
            })
            output_df = output_df.copy(deep=True)  # ensure a true deep copy is made
        except Exception as e:
            logger.error("Error creating output DataFrame: %s", e)
            raise

        return output_df

    def _extract_full_content(self, input_df: pd.DataFrame) -> pd.Series:
        """
        Extracts full content from the input DataFrame.

        :param input_df: Input DataFrame containing RSS feed entries from feedparser.
        :return: Series containing the full content.
        """
        if "content" in input_df.columns:
            return input_df["content"].apply(
                lambda x: x[0]["value"] if isinstance(x, list) and len(x) > 0 and "value" in x[0]
                else x if isinstance(x, str) else "No Content Available"
            )
        return pd.Series(["No Content Available"] * len(input_df))

    def _extract_categories(self, input_df: pd.DataFrame) -> pd.Series:
        """
        Extracts categories from the input DataFrame.

        :param input_df: Input DataFrame containing RSS feed entries from feedparser.
        :return: Series containing the categories.
        """
        if "tags" in input_df.columns:
            return input_df["tags"].apply(
                lambda x: [tag["term"] for tag in x] if isinstance(x, list) else []
            )
        return pd.Series([[]] * len(input_df))

    def _store_in_table_storage(self, table_client, output_df):
        """
        Stores processed RSS feed entries in Azure Table Storage.

        :param table_client: Azure Table Storage client.
        :param output_df: DataFrame containing enriched RSS feed entries.
        """
        table_name = "RSSFeedEntries"
        for _, row in output_df.iterrows():
            try:
                entity = {
                    "PartitionKey": row["Published_Date"][:7],  # Year-Month format for partitioning
                    "RowKey": row["Entry_ID"],
                    "Title": row["Title"],
                    "URL": row["URL"],
                    "Summary": row["Summary"],
                    "Sentiment": str(row["Sentiment"]),
                    "Readability": str(row["Readability"]),
                    "Embedding": json.dumps(row["Embedding"]),  # Store embeddings as JSON string
                }
                table_client.upsert_entity(entity)
                logger.info("Stored entry in Azure Table Storage: %s", row["Entry_ID"])
            except Exception as e:
                logger.error("Failed to store entry in Table Storage: %s | Error: %s", row["Entry_ID"], e)


    def _improve_summary(self, text: str, openai_client: ChatCompletionsClient) -> str:
        """
        Uses the ranking model to refine the existing summary from Feedparser.

        :param text: The original summary text to be improved.
        :param openai_client: The OpenAI client for generating the improved summary.
        :return: Improved summary text.
        """
        response = openai_client.complete(
            model=os.getenv("MODEL_RANKING"),
            messages=[{"role": "system", "content": "Improve this short summary for clarity and engagement, keeping it concise."},
                      {"role": "user", "content": text}],
            max_tokens=50
        )
        return response.choices[0].message.content.strip()

    def _analyze_sentiment(self, text: str, openai_client: ChatCompletionsClient) -> Tuple[str, float]:
        """
        Uses ranking model to perform sentiment analysis.

        :param text: The text to analyze for sentiment.
        :param openai_client: The OpenAI client for performing sentiment analysis.
        :return: Sentiment score between -1 and 1.
        """
        try:
            response = openai_client.complete(
                model=os.getenv("MODEL_RANKING"),
                messages=[{"role": "system", 
                           "content": "Analyze the sentiment of this text. Categorized it as one of " + 
                                    "Positive, Negative, Neutral, or Mixed and return a score between -1 and 1. " +
                                    "Output should be in the format: { \"sentiment\": \"Positive\", \"score\": 0.8 }."},
                          {"role": "user", 
                           "content": text}],
                max_tokens=20
            )
            result = json.loads(response.choices[0].message.content.strip())
            logger.info("Sentiment analysis successful for text: %s", text[:100])
            return result["sentiment"], float(result["score"])
        except Exception as e:
            logger.error("Failed to analyze sentiment for text: %s | Error: %s", text[:100], e)
            return "Error", 0.0

    def _compute_readability(self, text):
        """
        Computes readability using a simple Flesch-Kincaid formula approximation.

        :param text: The text to compute readability for.
        :return: Readability score.
        """
        words = text.split()
        sentences = text.count(".") + text.count("!") + text.count("?")
        return round(206.835 - 1.015 * (len(words) / max(1, sentences)) - 84.6 * (sum(map(len, words)) / max(1, len(words))), 2)

    def _generate_embedding(self, text, openai_client):
        """
        Generates an embedding for topic classification.

        :param text: The text to generate an embedding for.
        :param openai_client: The OpenAI client for generating the embedding.
        :return: Embedding vector.
        """
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding