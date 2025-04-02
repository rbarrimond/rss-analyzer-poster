"""
Azure Function App

This module defines the Azure Functions for handling RSS feed operations:
1. enqueRssFeeds - Scheduled to run daily at 6 AM UTC to queue new RSS feeds via RssQueueingService.
2. enqueRssFeedsHttp - HTTP-triggered endpoint to enqueue RSS feeds.
3. updateLogLevel - HTTP-triggered endpoint to dynamically update the logging level.

Also includes an internal helper to extract JSON from HTTP requests.
"""

import os
import json

import azure.functions as func
from azure.functions import HttpRequest, HttpResponse, QueueMessage

from services.rss import RssIngestionService
from utils.decorators import log_and_ignore_error, log_and_return_default
from utils.logger import LoggerFactory

# Configure logging
logger = LoggerFactory.get_logger(__name__, os.getenv("LOG_LEVEL", "INFO"))

# Create the Azure Functions application instance
app = func.FunctionApp()


@log_and_ignore_error("enque_rss_feeds function failed.")
@app.function_name(name="enqueueRssFeeds")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
def enqueue_rss_feeds(myTimer: func.TimerRequest) -> None:
    """
    Scheduled function triggered at 6 AM UTC daily.
    Invokes RssIngestionService to enqueue RSS feeds for subsequent processing.

    Parameters:
        myTimer (func.TimerRequest): Timer details for the scheduled trigger.

    Returns:
        None
    """
    logger.info('RSS Ingestion Service triggered.')

    _ = myTimer  # This is a placeholder for any future processing of the timer details.
    # Currently, it just logs the timer details but does not use them.

    RssIngestionService().enqueue_feeds()
    logger.info('RSS Ingestion Service completed.')


@log_and_return_default(
    func.HttpResponse('{"error": "Failed to enque RSS feeds."}',
                      status_code=500, mimetype="application/json"),
    message="enque_rss_feeds_http function failed."
)
@app.function_name(name="enqueueRssFeedsHttp")
@app.route(route="rss/enqueue", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def enque_rss_feeds_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered function to enqueue RSS feeds.
    Processes a POST request by optionally extracting request data, then calls RssIngestionService to start RSS ingestion.

    Parameters:
        req (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponse: JSON response indicating success or failure.
    """
    logger.info('RSS Ingestion Service triggered.')

    # This is a placeholder for any future processing of the request body.
    # Currently, it just extracts the JSON but does not use it.
    _ = _extract_json_from_request_body(req)

    RssIngestionService().enqueue_feeds()
    logger.info('RSS Ingestion Service completed.')

    return func.HttpResponse('{"message": "RSS feeds enqueued successfully."}', status_code=200, mimetype="application/json")


@log_and_return_default(
    func.HttpResponse('{"error": "Log level update failed."}',
                      status_code=500, mimetype="application/json"),
    message="update_log_level function failed."
)
@app.function_name(name="updateLogLevel")
@app.route(route="logs/update", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def update_log_level(req: HttpRequest) -> HttpResponse:
    """
    HTTP-triggered function to update the logging level.
    Reads the 'log_level' from the JSON payload and updates the logger accordingly.

    Parameters:
        req (HttpRequest): The incoming HTTP request containing the desired log level.

    Returns:
        HttpResponse: JSON response confirming the update or detailing an error.
    """
    logger.info('Update Log Level HTTP triggered.')

    new_level = _extract_json_from_request_body(req).get('log_level')
    if not new_level:
        return func.HttpResponse('{"error": "Missing \'log_level\' parameter in request."}', status_code=400, mimetype="application/json")
    LoggerFactory.update_handler_level(logger, new_level)

    return func.HttpResponse(f'{{"message": "Log level updated to {new_level}."}}', status_code=200, mimetype="application/json")


@log_and_ignore_error("ingest_queued_feed function failed.")
@app.function_name(name="ingestQueuedFeed")
@app.queue_trigger(arg_name="msg", queue_name=os.getenv("RSS_FEED_QUEUE_NAME"), connection="AzureWebJobsStorage")
def ingest_queued_feed(msg: QueueMessage) -> None:
    """
    Queue trigger function that processes messages from the RSS entry queue.
    Extracts the feed URL from the queue message and calls RssIngestionService.ingest_feed.
    
    Parameters:
        msg (func.QueueMessage): The triggered queue message.
        
    Returns:
        None
    """
    logger.info("Ingest Queued Feed received a message.")
    
    payload = _extract_json_from_queue_msg(msg)
    if not payload:
        logger.error("Empty message payload received.")
        return
    logger.debug("Ingest Queued Feed payload: %s", payload)

    feed_url = payload.get("feed", {}).get("url")
    if not feed_url:
        logger.error("Missing feed url in message payload.")
        return
    
    RssIngestionService().ingest_feed(feed_url)
    logger.info("Feed ingestion completed for: %s", feed_url)
        

@log_and_return_default(default_value={}, message="Failed to extract JSON from request.")
def _extract_json_from_request_body(req: HttpRequest) -> dict:
    """
    Helper function to extract JSON from an HTTP request's body.

    Parameters:
        req (HttpRequest): The HTTP request to parse.

    Returns:
        dict: The parsed JSON content.
    """
    return req.get_json()


@log_and_return_default(default_value={}, message="Failed to extract JSON from message.")
def _extract_json_from_queue_msg(msg: func.QueueMessage) -> dict:
    """
    Helper function to extract JSON from a queue message's body.
    
    Parameters:
        msg (func.QueueMessage): The queue message to parse.
        
    Returns:
        dict: The parsed JSON content.
    """
    return json.loads(msg.get_body().decode('utf-8'))
