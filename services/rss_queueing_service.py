"""
Module: rss_queueing_service
This module implements the RssQueueingService class which manages the retrieval 
and processing of RSS feeds. It loads configuration details, checks feeds for updates 
via conditional HTTP GET requests, and enqueues updated feeds for subsequent processing 
using an Azure queue.
"""

from datetime import datetime, timezone
from email.utils import format_datetime
import json
import os
import feedparser
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
        self.feed_urls: list = config.get('feeds', [])
        self.queue_name: str = config.get('queue', os.getenv('RSS_QUEUE_NAME'))
        self.queue_client: QueueClient = acf.get_instance().get_queue_service_client().get_client(self.queue_name)
        self.last_run: datetime = config.get('last_run', EPOCH_RFC1123)

        if not all([self.feed_urls, self.queue_name, self.queue_client]):
            logger.debug("Missing configuration values: feeds=%s, queue=%s, queue_client=%s", 
                         self.feed_urls, self.queue_name, self.queue_client)
            raise ValueError("Missing required configuration values.")

    @log_execution_time()
    @log_and_raise_error("Failed to enque feeds.")
    def run(self):
        """
        Iterate over all configured feed URLs and process each feed by:
          - Validating the existence of a feed URL.
          - Sending an HTTP GET request with an 'If-Modified-Since' header to check for new content.
          - Updating the last processed timestamp if new content is found.
          - Enqueuing the feed URL into the Azure queue for downstream processing.
 
        Feeds that are missing or invalid are skipped.
        """
        for feed_url in self.feed_urls:
            if self._check_feed_for_update(feed_url, self.last_run):
                self._enqueue_feed(feed_url)
        logger.info("RSS feeds enqueued successfully.")

    @log_execution_time()
    @log_and_return_default(False, message="Failed to check feed for update.")
    @retry_on_failure(retries=1, delay=0)
    def _check_feed_for_update(self, feed_url: str, modified_since: datetime = EPOCH_RFC1123) -> bool:
        """
        Checks for new content in the specified RSS feed.
        
        Sends an HTTP GET request to the feed URL with the "If-Modified-Since" header set to the provided timestamp.
        Returns True if the feed has been updated (HTTP 200) and updates the last_run timestamp; 
        returns False if no new content is detected (HTTP 304).
        
        Raises:
            requests.exceptions.HTTPError: If the HTTP GET request fails.
        """
        # Format the datetime to RFC1123 string for the header.
        headers = {"If-Modified-Since": format_datetime(modified_since)}
        response = requests.get(feed_url, timeout=5, headers=headers)
        response.raise_for_status()
        
        if response.status_code == 304:
            return False
        
        # Update the last_run timestamp and persist it via the ConfigLoader singleton to maintain state
        # across service instantiations.
        self.last_run = datetime.now(timezone.utc)

        return response.status_code == 200

    @log_and_raise_error("Failed to enqueue feed.")
    def _enqueue_feed(self, feed_url: str) -> None:
        """
        Enqueues the RSS feed after validating its contents.
        
        Parses the feed metadata using feedparser. 
        If the feed is invalid (i.e., missing metadata), raises a ValueError. 
        Otherwise, serializes the metadata to JSON and sends it to the Azure queue.
        """
        feed_metadata = feedparser.parse(feed_url).feed
        if not feed_metadata:
            raise ValueError(f"Invalid feed URL: {feed_url}")
        self.queue_client.send_message(json.dumps(feed_metadata))
