"""Module for RSS entry entity representation and persistence.

This module defines the Entry and AIEnrichment classes. Entry models an RSS
entry with properties such as title, link, and content. The content is cached,
hashed via xxhash, and stored in Azure Blob Storage. AIEnrichment handles
AI-based enhancements like summaries, readability scores, engagement data, and
embeddings.
"""

from functools import cached_property
import io
import os
from datetime import datetime
from typing import Any, Literal, Optional, Set

import numpy as np
import requests
import xxhash
from azure.data.tables import TableClient
from azure.storage.blob import ContainerClient
from bs4 import BeautifulSoup
from pydantic import (BaseModel, ConfigDict, Field, HttpUrl, computed_field,
                      field_validator)

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_raise_error, log_and_return_default, retry_on_failure
from utils.helper import truncate_by_sentences
from utils.logger import LoggerFactory
from utils.parser import parse_date

MAX_SUMMARY_SENTENCES = 20
MAX_SUMMARY_CHARACTERS = 2000

# Placeholder character for internal text processing, ensuring no conflicts with HTML content.
PRIVATE_SEPARATOR = "\uE000"

logger = LoggerFactory.get_logger(__name__)

entry_table_client: TableClient = acf.get_instance().get_table_service_client().get_table_client(
    table_name=os.getenv("RSS_ENTRIES_TABLE_NAME", "entries")
    )

ai_enrichment_table_client: TableClient = acf.get_instance().get_table_service_client().get_table_client(
    table_name=os.getenv("AI_ENRICHMENT_TABLE_NAME", "ai_enrichment")
    )

container_client: ContainerClient = acf.get_instance().get_blob_service_client().get_container_client(
    os.getenv("RSS_ENTRY_CONTAINER_NAME", "entries")
    )

class Entry(BaseModel):
    """Represents an RSS entry entity.

    Attributes:
        partition_key: Partition key for Azure Table Storage, used to organize entries into logical groups.
        title: Title of the entry, limited to 200 characters.
        id: Internal unique identifier of the entry, distinct from the entry's link.
        feed_key: RowKey of the feed to which this entry belongs, represented as a 16-character hexadecimal string.
        link: URL link to the entry, validated as a proper HTTP or HTTPS URL.
        published: Published date of the entry, defaulting to the Unix epoch if not provided.
        author: Author of the entry, limited to 50 characters.
        summary: Summary of the entry, truncated to a maximum of 2000 characters or 20 sentences.
        source: Source information for the entry, stored as a dictionary.
        content: Content of the entry, retrieved from Azure Blob Storage or via HTTP if not cached.
        row_key: Computed row key derived from the entry's id using xxhash.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True,
        strict=False,
        extra="ignore",
        field_serialization_order=[
            "PartitionKey",  # Azure Table partition key
            "RowKey",        # Internal hash ID used as RowKey
            "FeedKey",
            "Id",
            "Title",
            "Link",
            "Published",
            "Author",
            "Summary",
            "Source",
            "Content"        # Blob-backed field
        ]
    )
    
    partition_key: str = Field(
        default="entry",
        alias="PartitionKey",
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Partition key (alphanumeric, dash, underscore only) to ensure a valid blob path."
        )
    id: str = Field(
        alias="Id",
        min_length=1,
        max_length=200,
        description="Original ID from the RSS feed. Used only as a source identifier and is not guaranteed to be unique or stable."
        )
    feed_key: str = Field(
        alias="FeedKey",
        min_length=16,
        max_length=16,
        pattern=r"^[a-f0-9]{16}$",
        description="RowKey of the feed to which this entry belongs."
        )
    title: str = Field(
        default="Untitled",
        alias="Title",
        min_length=1,
        max_length=200,
        description="Title of the entry."
        )
    link: HttpUrl = Field(
        alias="Link",
        description="URL link to the entry. Must be a valid HTTP or HTTPS URL."
        )
    published: datetime = Field(
        default=datetime(1970, 1, 1),
        alias="Published",
        description="Published date of the entry."
        )
    author: Optional[str] = Field(
        default=None,
        alias="Author",
        description="Author of the entry.",
        max_length=50
        )
    summary: Optional[str] = Field(
        default=None,
        alias="Summary",
        description="Summary of the entry.",
        max_length=MAX_SUMMARY_CHARACTERS
        )
    source: Optional[dict] = Field(
        default=None,
        alias="Source",
        description="Source of the entry."
        )

    # def model_post_init(self, __context):
    #     """
    #     Initialize the _content attribute from the context data.

    #     This is used to retrieve the content from the context if available.
    #     This can happen if this entry is initialized with feed data
    #     and the content is already available.
    #     """
    #     self.content = __context.get("data", {}).get("content")

    @field_validator("summary", mode="before")
    @classmethod
    def clean_and_truncate_summary(cls, v):
        """
        Clean and truncate the summary to a specified number of sentences or characters.

        Args:
            v (str): The summary text to clean and truncate.

        Returns:
            str: The cleaned and truncated summary, or None if the input is empty.
        """
        if not v:
            return v
        cleaned = BeautifulSoup(v, "html.parser").get_text(separator=PRIVATE_SEPARATOR, strip=True)
        logger.debug("Cleaned summary: %s", cleaned)
        return truncate_by_sentences(cleaned, MAX_SUMMARY_SENTENCES, MAX_SUMMARY_CHARACTERS)

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

    @computed_field(alias="RowKey", 
                    description="RowKey of the entry in Azure Table Storage, computed from the RSS entry's id.")
    @cached_property
    def row_key(self) -> str:
        """
        Compute and return the row key derived from the entry's id.

        Returns:
            str: The computed row key as a hexadecimal hash.
        """
        return xxhash.xxh64(self.id).hexdigest()

    @computed_field(alias="Content", description="Cached content of the entry.")    
    @cached_property
    def content(self) -> Optional[str]:
        """
        Retrieve the content of the entry.

        If the content is not already cached, it attempts to fetch it from Azure Blob Storage or via HTTP.

        Returns:
            Optional[str]: The content of the entry, or None if not available.
        """
        return self._get_content_blob() or self._get_content_http()

    # @content.setter
    # def content(self, value: str) -> None:
    #     """
    #     Set the content of the entry.

    #     Args:
    #         value (str): The content to set.
    #     """
    #     self.__dict__["content"] = value

    @field_validator("published", mode="before")
    @classmethod
    def validate_published(cls, v: Any) -> Any:
        """
        Validates and converts the 'published' field to a datetime object.

        This method ensures that the 'published' field is always a datetime object,
        regardless of whether it was stored as a string, timestamp, or another type in Azure Table Storage.

        Args:
            v (Any): The value of the 'published' field, which may be a string, timestamp, or datetime object.

        Returns:
            datetime: The validated 'published' field as a datetime object.
        """
        return parse_date(v)

    @log_and_raise_error("Failed to save entry")
    def save(self) -> None:
        """
        Save or update the Entry instance in Azure Table Storage.

        Serializes the current state of the Entry and updates the corresponding entity record in storage.
        """
        if not self.content:
            raise ValueError("Content is not available.")
        self._persist_content()
        entry_table_client.upsert_entity(self.model_dump(mode="json", by_alias=True))

    @log_and_raise_error("Failed to delete entry")
    def delete(self) -> None:
        """
        Delete the Entry instance from Azure Table Storage.

        Removes the corresponding entity record using its partition and row keys.
        """
        container_client.delete_blob(blob=f"{self.partition_key}/{self.row_key}.txt")
        entry_table_client.delete_entity(self.partition_key, self.row_key)

    @log_and_return_default(default_value=None, message="Failed to retrieve content blob")
    def _get_content_blob(self) -> Optional[str]:
        """
        Retrieve the content blob from Azure Blob Storage.

        The blob is identified by a combination of the partition key and the content key.

        Returns:
            Optional[str]: The content as a string, or None if the blob is not available.
        """
        blob_name = f"{self.partition_key}/{self.row_key}_content.txt"
        blob = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=blob_name,
        )
        if not blob:
            raise ValueError(f"Blob {blob_name} not available.")
        return blob
    
    @log_and_return_default(default_value=None, message="Failed to retrieve content from HTTP")
    @retry_on_failure(retries=1, delay=2000)
    def _get_content_http(self) -> Optional[str]:
        """
        Retrieve the content via HTTP from the entry's link.

        Attempts to download the entry content with a timeout. If the response status is 200, returns the text;
        otherwise, raises an HTTP error.

        Returns:
            Optional[str]: The content of the entry, or None if the HTTP request fails.
        """
        response = requests.get(self.link, timeout=10)
        return response.text if response.status_code == 200 else response.raise_for_status()

    @log_and_raise_error("Failed to persist content")
    @retry_on_failure(retries=1, delay=2000)
    def _persist_content(self) -> None:
        """
        Persist the content to Azure Blob Storage.

        Computes a hash of the content and uploads it to Azure Blob Storage under a path based on the partition key
        and the computed content hash.
        """
        if not self.content:
            raise ValueError("Content is not available from cache.")
        container_client.get_blob_client(
            blob=f"{self.partition_key}/{self.row_key}_content.txt"
        ).upload_blob(self.content, overwrite=True)


class AIEnrichment(BaseModel):
    """Represents an AI enrichment entity associated with an RSS entry.

    Attributes:
        partition_key: Inherited partition key from the associated entry.
        row_key: Computed row key derived from the associated entry's id.
        summary: AI-generated summary of the entry.
        grade_level: Flesch-Kincaid readability score.
        difficulty: Dale-Chall readability score.
        engagement_score: Engagement score for the entry.
        engagement_categories: List of engagement categories (e.g., 'Liked', 'Comment', 'Shared').
        embeddings: AI-generated embeddings as a numpy array; retrieved from Azure Blob Storage if not already cached.
    """
    model_config = ConfigDict(
        populate_by_name=True, 
        from_attributes=True, 
        validate_assignment=True,
        arbitrary_types_allowed=True,
        strict=False,
        extra="ignore",
        field_serialization_order=[
            "PartitionKey",
            "RowKey",
            "Summary",
            "GradeLevel",
            "Difficulty",
            "EngagementScore",
            "EngagementCategories",
            "Embeddings"
        ]
    )
    
    partition_key: str = Field(
        default="entry",
        alias="PartitionKey",
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Partition key of the associated entry (alphanumeric, dash, underscore only) to ensure a valid blob path."
        )
    row_key: str = Field(
        default="entry",
        alias="PartitionKey",
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Row key of the associated entry (alphanumeric, dash, underscore only) to ensure a valid blob path."
        )
    summary: Optional[str] = Field(
        default=None,
        alias="Summary",
        max_length=MAX_SUMMARY_CHARACTERS,
        description="AI generated summary"
        )
    grade_level: Optional[float] = Field(
        default=None,
        alias="GradeLevel",
        ge=0,
        le=15.0,
        description="Flesch-Kincaid readability score (0 = easiest, 12 = high school, 15+ = complex academic text)"
        )
    difficulty: Optional[float] = Field(
        default=None,
        alias="Difficulty",
        ge=4.9,
        le=11.0,
        description="Dale-Chall readability score (4.9 = easy, 8.0 = difficult, 10+ = very difficult)"
        )    
    engagement_score: Optional[float] = Field(
        default=None,
        alias="EngagementScore",
        ge=0,
        le=10,
        description="Engagement score"
        )
    engagement_categories: Optional[Set[Literal['Liked', 'Comment', 'Shared']]] = Field(
        default=None,
        alias="EngagementCategories",
        max_items=3,
        min_items=1,
        description="Categories of engagement"
        )

    # def model_post_init(self, __context):
    #     """
    #     Initialize the embeddings attribute from the context data.

    #     This is used to retrieve the embeddings from the context if available.
    #     """
    #     self.embeddings = __context.get("data", {}).get("embeddings")

    @computed_field(alias="Embeddings", description="Cached embeddings of the entry.")
    @cached_property
    def embeddings(self) -> Optional[np.ndarray]:
        """
        Retrieve the embeddings numpy array from Azure Blob Storage.

        If the embeddings are not already cached, fetch them from Azure Blob Storage.

        Returns:
            Optional[np.ndarray]: The embeddings numpy array, or None if not available.
        """
        return self._get_embeddings_blob

    # @embeddings.setter
    # def embeddings(self, value: np.ndarray) -> None:
    #     """
    #     Set the embeddings numpy array.

    #     Args:
    #         value (np.ndarray): The embeddings to set.
    #     """
    #     self.__dict__["embeddings"] = value

    @log_and_raise_error("Failed to save AI enrichment")
    def save(self) -> None:
        """
        Save the current AIEnrichment instance to Azure Table Storage.
        """
        self._persist_embeddings()
        ai_enrichment_table_client.upsert_entity(self.model_dump(mode="json", by_alias=True))
    
    @log_and_raise_error("Failed to delete AI enrichment")
    def delete(self) -> None:
        """
        Delete the AIEnrichment instance from Azure Table Storage using its partition and row keys.
        """
        ai_enrichment_table_client.delete_entity(self.partition_key, self.row_key)
    
    @log_and_return_default(default_value=None, message="Failed to retrieve embeddings blob")
    def _get_embeddings_blob(self) -> Optional[np.ndarray]:
        """
        Retrieve and load the embeddings numpy array from Azure Blob Storage.

        Returns:
            Optional[np.ndarray]: The embeddings numpy array, or None if the blob is not available.
        """
        blob_bytes = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self.partition_key}/{self.row_key}.npy",
        )
        return np.load(io.BytesIO(blob_bytes)) if blob_bytes else None

    @log_and_raise_error("Failed to persist embeddings")
    @retry_on_failure(retries=1, delay=2000)
    def _persist_embeddings(self) -> None:
        """
        Persist the embeddings numpy array to Azure Blob Storage.

        Serializes the numpy array and uploads it to Azure Blob Storage.
        """
        with io.BytesIO() as buf:
            np.save(buf, self.embeddings)
            buf.seek(0)
            container_client.upload_blob(
                name=f"{self.partition_key}/{self.row_key}.npy",
                data=buf.getvalue(),
                overwrite=True
            )
        logger.debug("Embeddings %s/%s persisted to blob storage.", self.partition_key, self.row_key)
