"""
Module: rss_queueing_service
This module implements the RssQueueingService class which manages the retrieval 
and processing of RSS feeds. It loads configuration details, checks feeds for updates 
via conditional HTTP GET requests, and enqueues updated feeds for subsequent processing 
using an Azure queue.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime
import os
import requests
from azure.storage.queue import QueueClient

from utils.azclients import AzureClientFactory as acf
from utils.config import ConfigLoader
from utils.decorators import (log_and_raise_error, log_and_return_default,
                              log_execution_time, retry_on_failure,
                              trace_class)
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)

EPOCH_RFC1123 = datetime(1970, 1, 1)

@trace_class
class RssQueueingService:
    """
    RssQueueingService orchestrates the processing of configured RSS feeds.
    It performs the following:
      - Loads feeds configuration and required Azure resources.
      - Checks each RSS feed for newly published content using HTTP GET requests 
        with 'If-Modified-Since' headers.
      - Enqueues the URLs of updated feeds for downstream processing.
    
    Raises:
        ValueError: If essential configuration values (feeds, queue name, or queue client) are missing.
    """
    @log_and_raise_error("❌ Failed to initialize RssQueueingService.")
    def __init__(self):
        """
        Initializes the RssQueueingService by:
          - Loading the list of RSS feeds and the Azure queue name from configuration or environment variables.
          - Instantiating the Azure QueueClient.
          - Setting the last processed time to a default value if not provided.
          
        Raises:
          ValueError: If any required configuration (feeds, queue name, or queue client) is absent.
        """
        config: dict = ConfigLoader().RssQueueingService
        self.feeds: list = config.get('feeds', [])
        self.queue_name: str = config.get('queue', os.getenv('RSS_QUEUE_NAME'))
        self.queue_client: QueueClient = acf.get_instance().get_queue_service_client().get_client(self.queue_name)
        self.last_run: datetime = config.get('last_run', EPOCH_RFC1123))

        if not all([self.feeds, self.queue_name, self.queue_client]):
            raise ValueError("Missing required configuration values.")

    @log_execution_time()
    @log_and_raise_error("Failed to process feeds.")
    def process_feeds(self):
        """
        Processes each configured RSS feed by:
          - Validating that a feed has a valid URL.
          - Performing an HTTP GET request with a conditional header based on the last processed timestamp.
          - Enqueuing the feed URL if an update is detected.
          
        Feeds with missing or invalid URLs are ignored.
        """
        for feed in self.feeds:
            feed_url = feed.get('url')
            if feed_url and self._check_feed_for_update(feed_url, self.last_run):
                self._enqueue_feed(feed_url)

    @log_execution_time()
    @log_and_return_default(False, message="Failed to check feed for update.")
    @retry_on_failure(retries=1, delay=0)  # ...existing decorators...
    def _check_feed_for_update(self, feed_url: str, modified_since: datetime = EPOCH_RFC1123) -> bool:
        """
        Checks whether the specified RSS feed has new content.

        Args:
            feed_url (str): The URL of the RSS feed.
            modified_since (datetime): A datetime object used as a reference for updates.
                Defaults to EPOCH_RFC1123.
        
        Returns:
            bool: True if the feed returns updated content (HTTP 200), or False if no new content is found (HTTP 304).
        
        Raises:
            requests.exceptions.HTTPError: If the HTTP GET request fails.
        """
        # Format the datetime to RFC1123 string for the header.
        headers = {"If-Modified-Since": format_datetime(modified_since)}
        response = requests.get(feed_url, timeout=5, headers=headers)
        response.raise_for_status()
        if response.status_code == 304:
            return False
        else:
            self.last_run = datetime.now(timezone.utc)
            return response.status_code == 200

    @log_and_raise_error("Failed to enqueue feed.")
    def _enqueue_feed(self, feed_url: str) -> None:
        """
        Enqueues the given RSS feed URL into the Azure queue for further processing.

        Args:
            feed_url (str): The URL of the updated RSS feed.
        
        Utilizes an Azure QueueClient instance to send the URL message to the queue.
        """
        self.queue_client.send_message(feed_url)
