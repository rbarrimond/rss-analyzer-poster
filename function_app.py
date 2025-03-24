"""
Azure Function App

This module defines the Azure Functions for handling RSS feed operations:
1. enqueRssFeeds - Scheduled to run daily at 6 AM UTC to queue new RSS feeds via RssQueueingService.
2. enqueRssFeedsHttp - HTTP-triggered endpoint to enqueue RSS feeds.
3. updateLogLevel - HTTP-triggered endpoint to dynamically update the logging level.

Also includes an internal helper to extract JSON from HTTP requests.
"""

import azure.functions as func
from azure.functions import HttpRequest, HttpResponse

from utils.decorators import log_and_ignore_error, log_and_return_default
from utils.logger import LoggerFactory
from services.rss_queueing_service import RssQueueingService

# Configure logging
logger = LoggerFactory.get_logger(__name__)

# Create the Azure Functions application instance
app = func.FunctionApp()

@app.function_name(name="enqueueRssFeeds")
@app.schedule(schedule="0 0 6 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=True)
@log_and_ignore_error("enque_rss_feeds function failed.")
def enque_rss_feeds(myTimer: func.TimerRequest) -> None:
    """
    Queues RSS feeds daily at 6 AM UTC.
    
    This function is triggered by a timer and activates RssQueueingService
    to process the RSS feeds.
    
    Parameters:
        myTimer (func.TimerRequest): The timer trigger object.
        
    Returns:
        None
    """
    logger.info('RSS Queueing Service triggered.')
    RssQueueingService().run()

@app.function_name(name="enqueueRssFeedsHttp")
@app.route(route="rss/enqueue", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
@log_and_return_default(
    func.HttpResponse('{"error": "Failed to enque RSS feeds."}', status_code=500, mimetype="application/json"),
    message="enque_rss_feeds_http function failed."
)
def enque_rss_feeds_http(req: HttpRequest) -> HttpResponse:
    """
    HTTP endpoint for enqueuing and processing RSS feeds.
    
    Receives a POST request, triggers the RssQueueingService, and returns a JSON response
    indicating whether the operation succeeded.
    
    Parameters:
        req (HttpRequest): The incoming HTTP request.
        
    Returns:
        HttpResponse: A JSON response with a success or error message.
    """
    logger.info('RSS Queueing Service triggered.')
    RssQueueingService().run()
    return func.HttpResponse('{"message": "RSS feeds enqueued successfully."}', status_code=200, mimetype="application/json")

@app.function_name(name="updateLogLevel")
@app.route(route="logs/update", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
@log_and_return_default(
    func.HttpResponse('{"error": "Log level update failed."}', status_code=500, mimetype="application/json"),
    message="update_log_level function failed."
)
def update_log_level(req: HttpRequest) -> HttpResponse:
    """
    Dynamically updates the logging level via an HTTP request.
    
    Accepts a POST request with a JSON payload containing the 'log_level' key. The logger's level
    is updated based on this parameter. Returns a JSON response confirming the update or an error
    message if the parameter is missing.
    
    Parameters:
        req (HttpRequest): The incoming HTTP request containing the desired log level.
        
    Returns:
        HttpResponse: A JSON response detailing the result of the update operation.
    """
    logger.info('Update Log Level HTTP triggered.')

    new_level = _extract_json_from_request_body(req).get('log_level')
    if not new_level:
        return func.HttpResponse('{"error": "Missing \'log_level\' parameter in request."}', status_code=400, mimetype="application/json")
    LoggerFactory.update_handler_level(logger, new_level)

    return func.HttpResponse(f'{{"message": "Log level updated to {new_level}."}}', status_code=200, mimetype="application/json")

@log_and_return_default(default_value={}, message="Failed to extract JSON from request.")
def _extract_json_from_request_body(req: HttpRequest) -> dict:
    """
    Extracts JSON data from the HTTP request body.
    
    Parameters:
        req (HttpRequest): The incoming HTTP request.
        
    Returns:
        dict: Parsed JSON from the request.
    """
    return req.get_json()
