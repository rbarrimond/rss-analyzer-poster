"""
Azure Function App

This module defines the Azure Functions for collecting and analyzing RSS feeds:
1. enqueueRssFeeds - Scheduled to run daily at 6 AM (UTC) to queue new RSS feeds via RssQueueingService,
   which then forwards the feeds via a queue to RssIngestionService for processing.
2. rssFeedProcessorHttp - HTTP-triggered endpoint to fetch and analyze RSS feeds on-demand.
3. rssSummarizerHttp - HTTP-triggered endpoint to summarize existing RSS articles without fetching new ones.
4. rssPosterHttp - HTTP-triggered endpoint to fetch RSS feeds without analyzing them.

Dependencies:
- Uses Azure Blob Storage for storing configuration files and role content.
- Integrates with Microsoft Graph API to interact with Microsoft Lists.
- Utilizes Azure OpenAI for generating summaries and engagement scores.

Environment Variables:
- Various environment variables are used for configuration, including Azure Blob Storage endpoints, 
  SharePoint site and list IDs, and Azure Key Vault URL for secrets.

Key Operations:
- Fetching RSS feeds from URLs specified in a configuration file stored in Azure Blob Storage.
- Storing RSS feed entries in Microsoft Lists.
- Analyzing and summarizing RSS feed entries using Azure OpenAI and updating Microsoft Lists with the results.

Logging:
- Logging is configured to provide detailed information about the operations performed by each function.
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
    Queues RSS feeds on a daily schedule (6 AM UTC).

    Parameters:
        myTimer (func.TimerRequest): Timer trigger object for the scheduled function.

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
    HTTP-triggered endpoint to enqueue and process RSS feeds.

    Parameters:
        req (HttpRequest): The incoming HTTP request.

    Returns:
        HttpResponse: Returns a success message with status code 200 or an error response.
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
    HTTP-triggered Function:
    Updates the log level of the logger based on the request parameter.

    :param req: The HTTP request object.
    :return: HTTP response indicating the result of the operation.
    """
    logger.info('Update Log Level HTTP triggered.')

    new_level = _extract_json_from_request_body(req).get('log_level')
    if not new_level:
        return func.HttpResponse('{"error": "Missing \'log_level\' parameter in request."}', status_code=400, mimetype="application/json")
    LoggerFactory.update_handler_level(logger, new_level)

    return func.HttpResponse(f'{{"message": "Log level updated to {new_level}."}}', status_code=200, mimetype="application/json")

@log_and_return_default(default_value={}, message="Failed to extract JSON from request.")
def _extract_json_from_request_body(req: HttpRequest) -> dict:
    return req.get_json()
