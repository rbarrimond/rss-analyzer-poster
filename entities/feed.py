"""Module for RSS feed entity representation and persistence.

This module defines the Feed class, which models an RSS feed with properties such as link, name, language,
publisher, and more. It computes a unique identifier using xxhash and integrates with Azure Table Storage
to perform create, update, delete, and serialization operations.
"""

from datetime import datetime
from typing import Optional
import os

import xxhash
from pydantic import BaseModel, Field, computed_field, HttpUrl, ConfigDict

from utils.azclients import AzureClientFactory as acf

TABLE_NAME = os.getenv("RSS_FEED_TABLE_NAME", "feeds")
table_client = acf.get_instance().get_table_service_client().get_table_client(table_name=TABLE_NAME)

class Feed(BaseModel):
    """
    Represents an RSS feed entity with properties such as link, name, language,
    publisher, and update timestamp. The unique identifier (row key) is computed 
    from the feed link using xxhash. This model integrates with Azure Table Storage
    by mapping model fields to table entity properties via field aliases.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True
    )
    _partition_key: str = Field(default="feed", alias="PartitionKey")
    name: Optional[str] = Field(default="Unknown Name", min_length=1, max_length=200)
    link: HttpUrl
    language: Optional[str] = Field(default=None, regex=r'^[a-z]{2}(?:-[A-Z]{2})?$')
    publisher: Optional[str] = Field(default=None, min_length=1, max_length=200)
    rights: Optional[str] = Field(default=None, max_length=500)
    updated: datetime = datetime(1970, 1, 1)
    image: Optional[dict] = None
    subtitle: Optional[str] = Field(default=None, max_length=300)

    @computed_field(alias="RowKey")
    @property
    def row_key(self) -> str:
        """
        Returns the unique identifier for the feed.
        """
        return xxhash.xxh64(self.link).hexdigest()
        
    @classmethod
    def create(cls, **kwargs) -> "Feed":
        """
        Create and persist a Feed instance.
        
        This method instantiates a Feed using the provided keyword arguments,
        computes its unique row key from the link if not already set,
        and immediately stores the instance in Azure Table Storage.
        
        Args:
            **kwargs: Arbitrary keyword arguments defining the Feed properties.
        
        Returns:
            Feed: The created and persisted Feed instance.
        """
        feed = cls(**kwargs)
        table_client.upsert_entity(feed.model_dump())
        return feed

    def save(self) -> None:
        """
        Save (or update) the Feed instance in Azure Table Storage.
        
        This method serializes the current state of the Feed and updates
        the corresponding record in the storage.
        """
        table_client.upsert_entity(self.model_dump())

    def delete(self) -> None:
        """
        Remove the Feed instance from Azure Table Storage.
        
        This method deletes the Feed record using its partition and row keys.
        """
        table_client.delete_entity(self._partition_key, self._row_key)
