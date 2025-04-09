"""
Module: rss_ingestion_service
This module handles the loading of configuration, conditional HTTP checking of RSS feeds for updates,
and enqueuing updated feeds (with entry IDs) into an Azure Queue for downstream processing.
"""

import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import List, Tuple

import feedparser
from pydantic import HttpUrl
import requests
from feedparser import FeedParserDict

from entities.entry import Entry
from entities.feed import Feed
from utils.azclients import AzureClientFactory as acf
from utils.config import ConfigLoader
from utils.decorators import (log_and_raise_error, log_and_return_default,
                              log_execution_time, retry_on_failure,
                              trace_class)
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)

# Default epoch time for last ingestion
# This is the Unix epoch time (1970-01-01T00:00:00Z) used as a fallback for last ingestion.
EPOCH_RFC1123 = datetime(1970, 1, 1)

class RssIngestionService:
    """
    The RssIngestionService class is responsible for managing RSS feed processing.
    It loads the configuration, checks for feed updates using conditional HTTP GET requests,
    and enqueues updated feeds along with their entry IDs for subsequent processing.

    This class uses the AzureClientFactory to send messages to Azure Queues.

    Raises:
        ValueError: If required configuration (feeds list or related values) is missing.

    Attributes:
        feeds (list): List of RSS feed configurations to process.
        last_ingestion (datetime): Timestamp indicating the last successful ingestion.
    """

    def __init__(self):
        """
        Initialize the RssIngestionService instance.

        Reads the feeds list and Azure queue settings from the configuration (or environment).
        Initializes a last_ingestion timestamp used to determine if feeds have new content.

        Raises:
            ValueError: When mandatory configuration values (feeds or queue settings) are absent.
        """
        config: dict = ConfigLoader().RssIngestionService
        self.feeds: list = config.get('feeds', [])
        self.last_ingestion: datetime = config.get('last_ingestion', EPOCH_RFC1123)

        if not self.feeds:
            logger.debug("Missing configuration values: feeds=%s", self.feeds)
            raise ValueError("Missing required configuration values.")

    @log_and_raise_error("RSS Ingestion Service failed to enqueue feeds")
    def enqueue_feeds(self):
        """
        Process each configured RSS feed by checking for updates and enqueuing updated feeds.

        For each feed URL, a conditional HTTP GET is performed using an 'If-Modified-Since'
        header. If new content is detected (HTTP 200), the feed is enqueued for downstream processing
        using the AzureClientFactory's send_to_queue method.

        After processing, the last_ingestion timestamp is updated in the configuration.
        """
        for feed in self.feeds:
            if self._check_feed_for_update(feed['url'], self.last_ingestion):

                payload = {
                    "envelope": {
                        "status": "enqueued",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "feed": feed,
                }

                acf.get_instance().send_to_queue(os.getenv('RSS_FEED_QUEUE_NAME'), payload)
                logger.debug("Enqueuing payload: %s", payload)

        # Update the last_run timestamp and persist it via the ConfigLoader singleton to maintain state
        # across service instantiations.
        ConfigLoader().RssIngestionService['last_ingestion'] = datetime.now(timezone.utc)
        logger.info("RSS Ingestion Service enqueued feeds successfully. Last run updated to: %s",
                    ConfigLoader().RssIngestionService['last_ingestion'])
        

    @log_and_return_default(False, message="Failed to check feed for update")
    @retry_on_failure(retries=1, delay=0)  # Retry once with delay coming from timeout in requests.get()
    def _check_feed_for_update(self, feed_url: str, modified_since: datetime = EPOCH_RFC1123) -> bool:
        """
        Check whether an RSS feed has been updated based on the provided timestamp.

        Sends a GET request with an 'If-Modified-Since' header formatted as RFC1123
        and a User-Agent header. Follows redirects to ensure the final resource is reached.

        Args:
            feed_url (str): The URL of the RSS feed to check.
            modified_since (datetime): The timestamp to use for the 'If-Modified-Since' header.

        Returns:
            bool: True if the feed returns HTTP 200 (indicating new content), False if HTTP 304.

        Raises:
            requests.exceptions.HTTPError: When the HTTP request fails.
        """
        # Format the datetime to RFC1123 string for the header.
        headers = {
            "If-Modified-Since": format_datetime(modified_since),
            "User-Agent": "Mozilla/5.0 (compatible; MyRSSFeedReader/1.0; +https://rlbenterprisesllc.com)"
        }
        # Explicitly allow redirections to handle any HTTP redirects.
        response = requests.get(feed_url, timeout=5, headers=headers, allow_redirects=True)
        response.raise_for_status()

        if response.status_code == 304:
            logger.debug("Feed at %s not updated.", feed_url)
            return False

        logger.debug("Feed at %s updated (final URL: %s).", feed_url, response.url)
        return response.status_code == 200

    @log_and_return_default(default_value=False, message="Failed to ingest feed")
    def ingest_feed(self, feed_url: str) -> bool:
        """
        Enqueue an RSS feed for further processing.

        Parses the RSS feed to retrieve metadata and extract entry IDs.
        Constructs a JSON payload that includes:
          - An envelope with the state "retrieved" and a current ISO-formatted timestamp.
          - The feed metadata.
          - A list of entry IDs.

        The payload is then sent to the Azure queue using the AzureClientFactory's send_to_queue method.

        Args:
            feed_url (str): The URL of the RSS feed to ingest.

        Raises:
            ValueError: If the feed metadata is missing, indicating an invalid RSS feed.
        """
        
        feed_data: FeedParserDict = feedparser.parse(feed_url)
        if not feed_data['feed']:
            logger.debug("Feed data is empty or invalid: %s", feed_data)
            raise ValueError(f"Feed data is empyt or invalid at URL: {feed_url}")
        logger.debug("Feed %s parsed at URL: %s", feed_data['feed']['title'], feed_url)

        # Update the Feed table with the feed metadata
        feed = Feed(**feed_data['feed'])
        if not feed.link:
            logger.debug("Feed link is missing in feed data: %s", feed_data['feed'])
            feed.link = HttpUrl(feed_url)
        logger.debug("Feed created: %s", feed)
       
        # The partition key is derived from the feed title, converted to snake_case
        partition_key = re.sub(r'(?<!^)(?=[A-Z])', '_', str(feed.title)).lower().strip()
        # Remove any characters not allowed (only alphanumeric, dash, and underscore are permitted)
        partition_key = re.sub(r'[^a-z0-9_-]', '', partition_key)
        logger.debug("Feed entry partition key: %s", partition_key)

        entry_keys: List[Tuple[str, str]] = []
        # Create the entries and persist them
        for entry in feed_data.entries:
            entry = Entry(partition_key=partition_key, feed_key=feed.row_key, **entry)
            # Force loading content to ensure it is persisted
            _ = entry.content
            entry.save()
            entry_keys.append((entry.partition_key, entry.row_key))
            logger.debug("Created entry: %s", entry.row_key)

        # Batch queue the feed and its entries for AI enrichment processing
        payload = {
            "envelope": {
                "status": "retrieved",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "feed": feed.row_key,
            "entries": entry_keys
        }

        acf.get_instance().send_to_queue(os.getenv('RSS_ENTRY_QUEUE_NAME'), payload)
        logger.info("Feed %s ingested and queued successfully.", feed_data['feed']['title'])

        return True
