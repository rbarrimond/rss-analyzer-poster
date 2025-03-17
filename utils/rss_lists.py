"""
rss_lists.py

This module defines utility functions for interacting with Microsoft Lists and processing RSS feed entries.

Key Functions:
1. fetch_processed_status - Fetches items from Microsoft List with necessary fields only to filter what has 
   and hasn't been processed.
2. create_output_df - Creates an output DataFrame with specific columns from the input DataFrame containing RSS feed entries.
3. post_feed_entries - Posts feed entries to Microsoft List.

Dependencies:
- Uses Microsoft Graph API to interact with Microsoft Lists.
- Uses pandas for DataFrame operations.

Logging:
- Logging is configured to provide detailed information about the operations performed by each function.
"""

import pandas as pd
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.models.field_value_set import FieldValueSet
from msgraph.generated.models.list_item import ListItem
from msgraph.generated.sites.item.lists.item.columns.columns_request_builder import \
    ColumnsRequestBuilder
from msgraph.generated.sites.item.lists.item.items.items_request_builder import \
    ItemsRequestBuilder

from utils.logger import configure_logging

# Configure logging
logger = configure_logging(__name__)

async def fetch_column_names(graph_service_client, site_id: str, list_id: str) -> pd.Series:
    """
    Fetches column names from Microsoft List.

    :param graph_service_client: The Microsoft Graph service client.
    :param site_id: The SharePoint site ID.
    :param list_id: The Microsoft List ID.
    :return: Series containing the column names.
    """
    try:
        # Define query parameters to select displayName and name fields
        query_params = ColumnsRequestBuilder.ColumnsRequestBuilderGetQueryParameters(select=["displayName", "name"])
        request_configuration = RequestConfiguration(query_parameters=query_params)
        
        logger.debug('Fetching columns from Microsoft List')
        
        # Fetch columns from the Microsoft List
        columns = await graph_service_client.sites.by_site_id(site_id).lists.by_list_id(list_id).columns.get(request_configuration=request_configuration)
        columns_df = pd.DataFrame([column for column in columns.value])
        columns_df = columns_df[['display_name', 'name']]
        
        # Keep only the rows in the literal list of names from create_output_df
        columns_df = columns_df[(columns_df['display_name'] == columns_df['name']) | (columns_df['name'].str.startswith('field_'))]
        required_names = ['Title', 'URL', 'Summary', 'Entry_ID', 'Published_Date', 'Full_Content',
                         'Categories', 'Author', 'Keywords', 'Sentiment', 'Readability_Score',
                         'Engagement_Score', 'Processed', 'Engagement_Type', 'Response_Received']
        columns_df = columns_df[columns_df['display_name'].isin(required_names)]

        logger.debug('Columns fetched: %s', columns_df)

        return columns_df.set_index('display_name')['name']
    except Exception as e:
        logger.warning('Failed to fetch columns from Microsoft List: %s', e)
        return None

async def fetch_processed_status(graph_service_client, site_id: str, list_id: str) -> pd.Series:
    """
    Fetches items from Microsoft List with necessary fields only to filter what has 
    and hasn't been processed.

    :param graph_service_client: The Microsoft Graph service client.
    :param site_id: The SharePoint site ID.
    :param list_id: The Microsoft List ID.
    :return: Series containing the processed items.
    """
    try:
        column_names = await fetch_column_names(graph_service_client, site_id, list_id)
        if (column_names is None):
            logger.warning('No columns names fetched from Microsoft List')
            return None
        logger.debug('Entry_ID field: %s, Processed field: %s', column_names['Entry_ID'], column_names['Processed'])

        # Define query parameters to expand fields and select Entry_ID and Processed fields
        query_params = ItemsRequestBuilder.ItemsRequestBuilderGetQueryParameters(
            expand=[f"fields($select={column_names['Entry_ID']},{column_names['Processed']})"])
        request_configuration = RequestConfiguration(query_parameters=query_params)
        
        # Fetch items from the Microsoft List
        logger.debug('Fetching items from Microsoft List')
        items = await graph_service_client.sites.by_site_id(site_id).lists.by_list_id(list_id).items.get(request_configuration=request_configuration)
        items_df = pd.DataFrame([item.fields.additional_data for item in items.value])
        logger.debug('Items fetched: %s', items_df)

        # Set the index to Entry_ID and get the Processed status
        items_status = items_df.set_index(column_names['Entry_ID'])[column_names['Processed']]
        logger.debug('Processed status: %s', items_status)
        return items_status
    except Exception as e:
        logger.warning('Failed to fetch items from Microsoft List: %s', e)
        return None

def create_output_df(fp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates an output DataFrame with predefined columns from the input DataFrame.

    :param fp_df: Input DataFrame containing RSS feed entries from feedparser.
    :return: Output DataFrame with specific columns for storing in Microsoft Lists.
    """
    required_columns = ['title', 'link']
    missing_columns = [
        col for col in required_columns if col not in fp_df.columns]

    if missing_columns:
        logger.error(
            'Missing required columns in input DataFrame: %s', missing_columns)
        return pd.DataFrame()  # Return an empty DataFrame if required columns are missing

    # Define all columns up front
    column_defaults = {
        "Title": "Untitled",
        "URL": "",
        "Summary": "No Summary Available",
        "Entry_ID": fp_df.index.astype(str),
        "Published_Date": "1970-01-01T00:00:00Z",
        "Full_Content": "No Content Available",
        # Multi-select field, needs a list per row
        "Categories": [[]] * len(fp_df),
        "Author": "Unknown Author",
        "Keywords": "",
        "Sentiment": "Neutral",
        "Readability_Score": 0.0,
        "Engagement_Score": 0,
        "Processed": False,
        # Multi-choice field, should be list per row
        "Engagement_Type": [[]] * len(fp_df),
        "Response_Received": False
    }

    # Create DataFrame with all expected columns
    output_df = pd.DataFrame(column_defaults, index=fp_df.index)

    # Override columns with actual data from `fp_df` (if available)
    output_df["Title"] = fp_df["title"]
    output_df["URL"] = fp_df["link"]
    output_df["Summary"] = fp_df["summary"] if "summary" in fp_df.columns else output_df["Summary"]
    output_df["Author"] = fp_df["author"] if "author" in fp_df.columns else output_df["Author"]
    output_df["Published_Date"] = fp_df["published"] if "published" in fp_df.columns else output_df["Published_Date"]

    # Extract content safely
    if "content" in fp_df.columns:
        output_df["Full_Content"] = fp_df["content"].apply(
            lambda x: x[0]["value"] if isinstance(
                x, list) and x else "No Content Available"
        )

    # Extract categories safely
    if "tags" in fp_df.columns:
        output_df["Categories"] = fp_df["tags"].apply(
            lambda x: [tag["term"] for tag in x] if isinstance(x, list) else []
        )

    return output_df

async def post_feed_entries(graph_service_client, output_df: pd.DataFrame, site_id: str, list_id: str) -> None:
    """
    Posts feed entries to Microsoft List.

    :param graph_service_client: The Microsoft Graph service client.
    :param output_df: DataFrame containing the feed entries to be posted.
    :param site_id: The SharePoint site ID.
    :param list_id: The Microsoft List ID.
    """
    column_names = await fetch_column_names(graph_service_client, site_id, list_id)
    if column_names is None:
        logger.warning('No columns names fetched from Microsoft List')
        return

    # Fetch existing items to check for duplicates
    existing_items = await fetch_processed_status(graph_service_client, site_id, list_id)
    if existing_items is None:
        logger.warning('Failed to fetch existing items from Microsoft List')
        return

    # Rename columns to match Microsoft List columns
    output_df.rename(columns=column_names.to_dict(), inplace=True)  
    for _, row in output_df.iterrows():
        entry_id = row[column_names['Entry_ID']]
        if entry_id in existing_items.index:
            logger.info('Skipping article with ID %s as it already exists in the list', entry_id)
            continue

        list_item = ListItem(fields=FieldValueSet(additional_data=row.to_dict()))
        try:
            logger.debug('Posting item to Microsoft List: %s', list_item)
            await graph_service_client.sites.by_site_id(site_id).lists.by_list_id(list_id).items.post(list_item)
            logger.info('Inserted article with ID %s', entry_id)
        except Exception as e:
            logger.warning('Failed to insert article with ID %s: %s', entry_id, e)
            logger.debug('Failed item data: %s', row.to_dict())
