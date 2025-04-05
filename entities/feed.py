"""
Module for representing and persisting RSS Feed entities.

This module defines the Feed class which encapsulates an RSS feed's properties
and integrates with Azure Table Storage for create, update, delete, and serialization
operations. The unique row key is computed from the feed link using xxhash.
"""

import os
import json
from datetime import datetime
from typing import Optional

import xxhash
from azure.data.tables import TableClient
from pydantic import (BaseModel, ConfigDict, Field, HttpUrl, computed_field, field_validator)

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_return_default
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)

table_client: TableClient = acf.get_instance().get_table_service_client().get_table_client(
    table_name=os.getenv("RSS_FEEDS_TABLE_NAME", "feeds"))

class Feed(BaseModel):
    """
    Represents an RSS feed entity stored in Azure Table Storage.

    This class encapsulates the properties and behaviors of an RSS feed, including creation,
    persistence, and deletion operations. A unique row key is computed using xxhash based on the feed link,
    ensuring consistency when interacting with the storage table.

    Attributes:
        title (Optional[str]): The feed's display title (1-200 characters). Defaults to "Untitled".
        link (HttpUrl): The URL of the RSS feed (1-500 characters). Must be a valid HTTP or HTTPS link.
        language (Optional[str]): ISO language code for the feed (e.g., "en" or "en-US").
        publisher (Optional[str]): The publisher of the feed (1-200 characters).
        rights (Optional[str]): Rights information associated with the feed (1-500 characters).
        updated (datetime): Timestamp of the last update (default represents the Unix epoch).
        image (Optional[dict]): A dictionary containing image details associated with the feed.
        subtitle (Optional[str]): A subtitle or brief description of the feed (1-500 characters).
        row_key (str): Public computed property; unique identifier for the feed derived from its link via xxhash.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True,
        extra="ignore"
        )
    
    partition_key: str = Field(
        default="feed",
        alias="PartitionKey",
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Partition key for Azure Table Storage; default is 'feed'."
    )
    title: Optional[str] = Field(
        default="Untitled",
        alias="Title",
        min_length=1,
        max_length=200,
        description="Title of the feed; defaults to 'Untitled'."
    )
    link: HttpUrl = Field(
        alias="Link",
        min_length=1,
        max_length=500,
        description="URL of the feed. Must be a valid HTTP or HTTPS link."
    )
    language: Optional[str] = Field(
        default=None,
        alias="Language",
        pattern=r'^[a-z]{2}(?:-[a-zA-Z]{2})?$',
        description="Language code of the feed, e.g., 'en' or 'en-US'."
    )
    publisher: Optional[str] = Field(
        default=None,
        alias="Publisher",
        min_length=1,
        max_length=200,
        description="Publisher of the feed."
    )
    rights: Optional[str] = Field(
        default=None,
        alias="Rights",
        max_length=500,
        description="Rights information for the feed."
    )
    updated: datetime = Field(
        default=datetime(1970, 1, 1),
        alias="Updated",
        description="Timestamp of the last update; defaults to the Unix epoch."
    )
    image: Optional[dict] = Field(
        default=None,
        alias="Image",
        description="Associated image for the feed, stored as a dictionary."
    )
    subtitle: Optional[str] = Field(
        default=None,
        alias="Subtitle",
        max_length=500,
        description="Subtitle of the feed."
    )

    @computed_field(alias="RowKey", description="Unique identifier for the feed computed from its link.")
    @property
    def row_key(self) -> str:
        """
        Computes and returns the unique identifier (row key) for the feed using xxhash.

        Returns:
            str: The computed hash of the feed link.
        """
        return xxhash.xxh64(str(self.link).encode("utf-8")).hexdigest()

    @classmethod
    @field_validator("image", mode="before")
    @log_and_return_default(default_value=None, message="Failed to parse image JSON")
    def deserialize_image(cls, v):
        """
        Deserializes the image field from JSON string to a dictionary.
        This method is invoked before validation to ensure that the image field
        is always a dictionary, regardless of how it was stored in Azure Table Storage.
        Args:
            v: The value of the image field, which may be a JSON string or a dictionary.
        Returns:
            dict: The deserialized image field as a dictionary.
        """
        return json.loads(v) if isinstance(v, str) else v

    @classmethod
    def create(cls, **kwargs) -> "Feed":
        """
        Instantiates a Feed from provided properties and persists it to Azure Table Storage.

        This method computes the unique identifier from the feed link (if not explicitly set)
        and immediately upserts the feed entity into the storage table.

        Args:
            **kwargs: Keyword arguments defining the Feed properties.

        Returns:
            Feed: The created and persisted Feed instance.
        """
        logger.debug("Creating Feed with kwargs: %s", kwargs)
        
        feed = cls.model_validate(dict(kwargs), strict=False)
        feed.save()
        
        logger.debug("Feed created: %s", feed)

        return feed

    def save(self) -> None:
        """
        Saves or updates the Feed instance in Azure Table Storage.

        This method serializes the Feed instance and upserts the corresponding record
        in the storage table.
        """
        table_client.upsert_entity(self.model_dump(mode="json", by_alias=True))

    def delete(self) -> None:
        """
        Deletes the Feed instance from Azure Table Storage.

        This method removes the feed record from the storage table using its partition key
        and computed row key.
        """
        table_client.delete_entity(self.partition_key, self.row_key)
