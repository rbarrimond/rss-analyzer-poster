"""Module for RSS feed entity representation and persistence.

This module defines the Feed class, which models an RSS feed with properties such as link, name, language,
publisher, and more. It computes a unique identifier using xxhash and integrates with Azure Table Storage
to perform create, update, delete, and serialization operations.
"""

from datetime import datetime
from typing import Optional
import os

import xxhash
from pydantic import BaseModel, Field, model_validator

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
    _partition_key: str = Field(default="feed", alias="PartitionKey")
    _row_key: Optional[str] = Field(default=None, alias="RowKey")
    name: Optional[str] = "Unknown Name"
    link: str
    language: Optional[str] = None
    publisher: Optional[str] = None
    rights: Optional[str] = None
    updated: datetime = datetime(1970, 1, 1)
    image: Optional[dict] = None
    subtitle: Optional[str] = None

    class Config:
        """
        Pydantic configuration for the Feed model.

        This configuration enables the use of alias fields during both serialization 
        and instantiation from dictionaries. It also supports creation of models 
        directly from attribute mappings.
        """
        populate_by_name = True  # Ensures alias fields work in serialization
        from_attributes = True  # Allows model creation from dicts

    @classmethod
    @model_validator(mode="before")
    def compute_row_key(cls, data):
        """
        Computes the unique identifier for the feed based on the link.
        """
        if 'link' in data and not data.get('_row_key'):
            data['_row_key'] = xxhash.xxh64(data['link']).hexdigest()
        return data

    @property
    def row_key(self) -> str:
        """
        Returns the unique identifier for the feed.
        """
        return self._row_key
    
    @row_key.setter
    def row_key(self, value: str):
        """
        Sets the unique identifier for the feed. This is a read-only property.
        
        Raises:
            AttributeError: This property is read-only and cannot be set.
        """
        raise AttributeError("This property is read-only and cannot be set.")
    
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
        table_client.upsert_entity(feed.model_dump(by_alias=True))
        return feed

    def save(self) -> None:
        """
        Save (or update) the Feed instance in Azure Table Storage.
        
        This method serializes the current state of the Feed and updates
        the corresponding record in the storage.
        """
        table_client.upsert_entity(self.model_dump(by_alias=True))

    def delete(self) -> None:
        """
        Remove the Feed instance from Azure Table Storage.
        
        This method deletes the Feed record using its partition and row keys.
        """
        table_client.delete_entity(self._partition_key, self._row_key)

    def to_json(self) -> str:
        """
        Convert the Feed instance to a JSON string.
        
        This method serializes the Feed properties using their defined aliases,
        producing a JSON representation.
        
        Returns:
            str: A JSON string representing the Feed.
        """
        return self.model_dump_json(by_alias=True)

    @classmethod
    def from_json(cls, json_str: str) -> "Feed":
        """
        Construct a Feed instance from a JSON string.
        
        This method parses the provided JSON string and creates a new Feed instance
        populated with the data.
        
        Args:
            json_str (str): A JSON formatted string containing Feed data.
        
        Returns:
            Feed: The Feed instance reconstructed from the JSON input.
        """
        return cls.model_validate_json(json_str)
