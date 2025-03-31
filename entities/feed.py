"""
Module for representing and persisting RSS Feed entities.

This module defines the Feed class which encapsulates an RSS feed's properties
and integrates with Azure Table Storage for create, update, delete, and serialization
operations. The unique row key is computed from the feed link using xxhash.
"""

import os
from datetime import datetime
from typing import Optional

import xxhash
from azure.data.tables import TableClient
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field

from utils.azclients import AzureClientFactory as acf

table_client: TableClient = acf.get_instance().get_table_service_client().get_table_client(
    table_name=os.getenv("RSS_FEED_TABLE_NAME", "feeds"))

class Feed(BaseModel):
    """
    Represents an RSS feed entity for Azure Table Storage operations.

    This model includes properties such as link, name, language, publisher, and update timestamp.
    A unique identifier (row key) is computed automatically from the feed link using xxhash.
    The model is configured to map its fields to the corresponding Azure Table Storage entity
    properties via field aliases.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True
    )
    _partition_key: str = Field(
        default="feed",
        alias="PartitionKey",
        regex=r"^[a-zA-Z0-9_-]+$",
        description="Partition key for Azure Table Storage; default is 'feed'."
    )
    name: Optional[str] = Field(
        default="Unknown Name",
        alias="Name",
        min_length=1,
        max_length=200,
        description="Name of the feed; defaults to 'Unknown Name'."
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
        regex=r'^[a-z]{2}(?:-[A-Z]{2})?$',
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
        min_length=1,
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
        min_length=1,
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
        return xxhash.xxh64(self.link).hexdigest()

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
        feed = cls(**kwargs)
        table_client.upsert_entity(feed.model_dump())
        return feed

    def save(self) -> None:
        """
        Saves or updates the Feed instance in Azure Table Storage.

        This method serializes the Feed instance and upserts the corresponding record
        in the storage table.
        """
        table_client.upsert_entity(self.model_dump())

    def delete(self) -> None:
        """
        Deletes the Feed instance from Azure Table Storage.

        This method removes the feed record from the storage table using its partition key
        and computed row key.
        """
        table_client.delete_entity(self._partition_key, self.row_key)
