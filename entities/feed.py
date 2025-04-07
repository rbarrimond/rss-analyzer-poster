"""
Module for representing and persisting RSS Feed entities.

This module defines the Feed class which encapsulates an RSS feed's properties
and integrates with Azure Table Storage for create, update, delete, and serialization
operations. The unique row key is computed from the feed link using xxhash.
"""

from functools import cached_property
import os
import json
from datetime import datetime
from typing import Any, Optional

import xxhash
from pydantic import (BaseModel, ConfigDict, Field, HttpUrl,
                      computed_field, field_serializer, field_validator)

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_raise_error
from utils.logger import LoggerFactory
from utils.parser import parse_date

logger = LoggerFactory.get_logger(__name__)

RSS_FEEDS_TABLE_NAME = os.getenv("RSS_FEEDS_TABLE_NAME")

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
        strict=False,
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
    @cached_property
    def row_key(self) -> str:
        """
        Computes and returns the unique identifier (row key) for the feed using xxhash.

        Returns:
            str: The computed hash of the feed link.
        """
        return xxhash.xxh64(str(self.link)).hexdigest()

    @field_validator("link", mode="before")
    @classmethod
    def validate_link(cls, v: Any) -> str:
        """
        Ensures the 'link' field is a valid string before being validated as an HttpUrl.

        Args:
            v (Any): The value of the 'link' field.

        Returns:
            str: The validated link as a string.
        """
        if isinstance(v, HttpUrl):
            return str(v)
        if not isinstance(v, str):
            raise ValueError("The 'link' field must be a valid URL string.")
        return v

    @field_validator("image", mode="before")
    @classmethod
    def deserialize_image(cls, v: Any) -> Any:
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

    @field_validator("updated", mode="before")
    @classmethod
    def validate_updated(cls, v: Any) -> Any:
        """
        Validates and converts the 'updated' field to a datetime object.

        This method ensures that the 'updated' field is always a datetime object,
        regardless of whether it was stored as a string or another type in Azure Table Storage.

        Args:
            v (Any): The value of the 'updated' field, which may be a string, timestamp, or datetime object.

        Returns:
            datetime: The validated 'updated' field as a datetime object.
        """
        return parse_date(v)
    
    @field_serializer("image", mode="wrap")
    def serialize_image(self, field, value, info):
        """
        Converts the image field from a dictionary to a JSON string for storage.

        This method ensures that the image field is serialized as a JSON string
        when saving the Feed instance to Azure Table Storage. If the value is None,
        it returns None instead of a JSON string.

        Args:
            field: The model field being serialized.
            value (dict | None): The image field value, which may be a dictionary or None.
            info: Serialization context information.

        Returns:
            str | None: The serialized image field as a JSON string, or None if the value is None.
        """
        _ , _ = field, info
        logger.debug("Serializing image field: %s", value)
        return json.dumps(value) if value else None

    @log_and_raise_error("Failed to save feed")
    def save(self) -> None:
        """
        Saves or updates the Feed instance in Azure Table Storage.

        This method serializes the Feed instance and upserts the corresponding record
        in the storage table.
        """
        acf.get_instance().table_upsert_entity(table_name=RSS_FEEDS_TABLE_NAME,
                                               entity=self.model_dump(mode="json", by_alias=True))
        logger.debug("Feed saved: %s", self.model_dump(mode="json", by_alias=True))

    @log_and_raise_error("Failed to delete feed")
    def delete(self) -> None:
        """
        Deletes the Feed instance from Azure Table Storage.

        This method removes the feed record from the storage table using its partition key
        and computed row key.
        """
        acf.get_instance().table_delete_entity(table_name=RSS_FEEDS_TABLE_NAME,
                                               entity=self.model_dump(mode="json", by_alias=True))
        logger.debug("Feed deleted: %s", self.model_dump(mode="json", by_alias=True))
