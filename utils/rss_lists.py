import pandas as pd
from msgraph.generated.sites.item.lists.item.items.items_request_builder import ItemsRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration
from utils.logger import configure_logging

# Configure logging
logger = configure_logging(__name__)

async def fetch_processed_status(graph_service_client, site_id: str, list_id: str) -> pd.DataFrame:
    """
    Fetches items from Microsoft List with necessary fields only to filter what has 
    and hasn't been processed.

    :param graph_service_client: The Microsoft Graph service client.
    :param site_id: The SharePoint site ID.
    :param list_id: The Microsoft List ID.
    :return: DataFrame containing the processed items.
    """
    try:
        query_params = ItemsRequestBuilder.ItemsRequestBuilderGetQueryParameters(
            expand=["fields(select=Entry_ID,Processed)"])
        request_configuration = RequestConfiguration(query_parameters=query_params)
        items = await graph_service_client.sites[site_id].lists[list_id].items.get(request_configuration=request_configuration)
        items_df = pd.DataFrame([item['fields'] for item in items])
        items_df.set_index('Entry_ID', inplace=True)
        return items_df
    except Exception as e:
        logger.warning('Failed to fetch items from Microsoft List: %s', e)
        return None

def create_output_df(fp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates an output DataFrame with specific columns from the input DataFrame.

    :param fp_df: Input DataFrame containing RSS feed entries from feedparser.
    :return: Output DataFrame with specific columns for storing in Microsoft Lists.
    """
    output_df = pd.DataFrame(index=fp_df.index)
    output_df['Title'] = fp_df['title'].fillna('No Title')
    output_df['URL'] = fp_df['link'].fillna('')
    output_df['Summary'] = fp_df['summary'].fillna('')
    output_df['Entry_ID'] = fp_df.index
    output_df['Published_Date'] = fp_df['published'].fillna('')
    output_df['Full_Content'] = fp_df['content'].apply(lambda x: x[0].get('value', '') if x else '')
    output_df['Categories'] = fp_df['tags'].apply(lambda x: ', '.join([tag['term'] for tag in x]) if x else '')
    output_df['Author'] = fp_df['author'].fillna('')
    output_df['Keywords'] = ''  # Placeholder for keyword extraction (comma-separated)
    output_df['Sentiment'] = ''  # Placeholder for sentiment analysis [Positive, Negative, Neutral, Mixed]
    output_df['Readability_Score'] = None  # Placeholder for readability score [0.00-100.00]
    output_df['Engagement_Score'] = None  # Placeholder for engagement score [0-1000]
    output_df['Processed'] = False
    output_df['Engagement_Type'] = ''  # Placeholder for engagement type [Shared, Liked, Commented, None]
    output_df['Response_Received'] = False
    return output_df
