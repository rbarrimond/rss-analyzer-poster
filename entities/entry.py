"""Module for RSS entry entity representation and persistence.

This module defines the Entry and AIEnrichment classes.
Entry models an RSS entry with properties such as title, link, and content.
The content is retrieved using a caching mechanism, hashed via xxhash,
and stored in Azure Blob Storage. AIEnrichment handles AI-based enhancements,
including summaries, readability scores, engagement data, and embeddings kept as numpy arrays.
"""

import io
import os
from datetime import datetime
from typing import Literal, Optional, Set

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

MAX_SUMMARY_SENTENCES = 20
MAX_SUMMARY_CHARACTERS = 2000
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
        content_key: Hash of the content, used as a unique identifier for the content blob in Azure Blob Storage.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        validate_assignment=True,
        extra="ignore"
        )
    
    partition_key: str = Field(
        default="entry",
        alias="PartitionKey",
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Partition key (alphanumeric, dash, underscore only) to ensure a valid blob path."
        )
    title: str = Field(
        default="Untitled",
        alias="Title",
        min_length=1,
        max_length=200,
        description="Title of the entry."
        )
    id: str = Field(
        alias="Id",
        min_length=1,
        max_length=200,
        description="Internal unique identifier of the entry. This is not the same as the entry's link."
        )
    feed_key: str = Field(
        alias="FeedKey",
        min_length=16,
        max_length=16,
        pattern=r"^[a-f0-9]{16}$",
        description="RowKey of the feed to which this entry belongs."
        )
    link: HttpUrl = Field(
        alias="Link",
        description="URL link to the entry. Must be a valid HTTP or HTTPS URL."
        )
    _content: Optional[str] = Field(
        default=None,
        exclude=True,
        description="Content of the entry. This is not persisted in Azure Table Storage."
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

    def model_post_init(self, __context):
        # Initialize the content attribute from the context data.
        # This is used to retrieve the content from the context if available.
        # This can happen if the this entry is initialzied with feed data
        # and the content is already available.
        self._content = __context.get("data", {}).get("content")

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

    @computed_field(alias="RowKey", include=True, description="RowKey of the entry in Azure Table Storage.")
    @property
    def row_key(self) -> str:
        """
        Compute and return the row key derived from the entry's id.

        Returns:
            str: The computed row key as a hexadecimal hash.
        """
        return xxhash.xxh64(self.id).hexdigest()
    
    @computed_field(alias="ContentKey", include=True, description="Content key for the entry.")
    @property
    def content_key(self) -> Optional[str]:
        """
        Compute and return the content key for the entry.

        The content key is a hash of the content. If the content is not available, it returns None.

        Returns:
            Optional[str]: The content key as a hexadecimal hash, or None if content is unavailable.
        """
        if self._content:
            return xxhash.xxh64(self._content).hexdigest()
        return None
    
    @computed_field(return_type=Optional[str])
    @property
    def content(self) -> Optional[str]:
        """
        Retrieve and return the content of the entry.

        The content is fetched from Azure Blob Storage if not already cached. If unavailable in storage, it is
        retrieved via HTTP from the entry's link.

        Returns:
            Optional[str]: The content of the entry, or None if not available.
        """
        if self._content is None:
            val = self._get_content_blob() or self._get_content_http()
            if val:
                self._content = val
        return self._content

    @log_and_raise_error("Failed to create entry")
    @classmethod
    def create(cls, **kwargs) -> "Entry":
        """
        Create a new Entry instance and save it to Azure Table Storage.

        Args:
            **kwargs: Keyword arguments containing the entry data.

        Returns:
            Entry: The created Entry instance.

        Raises:
            ValueError: If the data is invalid or the entry cannot be created.
        """
        entry = cls.model_validate(dict(kwargs), strict=False)
        entry.save()
        return entry

    @log_and_raise_error("Failed to save entry")
    def save(self) -> None:
        """
        Save or update the Entry instance in Azure Table Storage.

        Serializes the current state of the Entry and updates the corresponding entity record in storage.
        """
        if not self._content:
            raise ValueError("Content is not available.")
        self._persist_content()
        entry_table_client.upsert_entity(self.model_dump(mode="json", by_alias=True))

    @log_and_raise_error("Failed to delete entry")
    def delete(self) -> None:
        """
        Delete the Entry instance from Azure Table Storage.

        Removes the corresponding entity record using its partition and row keys.
        """
        container_client.delete_blob(
            blob=f"{self.partition_key}/{self.content_key}.txt"
        )
        entry_table_client.delete_entity(self.partition_key, self.row_key)

    @log_and_return_default(default_value=None, message="Failed to retrieve content blob")
    def _get_content_blob(self) -> Optional[str]:
        """
        Retrieve the content blob from Azure Blob Storage.

        The blob is identified by a combination of the partition key and the content key.

        Returns:
            Optional[str]: The content as a string, or None if the blob is not available.
        """
        key = self.content_key
        if not key:
            raise ValueError("Content key is not available.")
        blob = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self.partition_key}/{key}.txt",
        )
        if not blob:
            raise ValueError("Blob not available.")
        return blob
    
    @log_and_return_default(default_value=None, message="Failed to retrieve content")
    @retry_on_failure(retries=3, delay=2000)
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

        Args:
            value (str): The content to be persisted.
        """
        if not self._content:
            raise ValueError("Content is not available.")
        hashed = xxhash.xxh64(self._content).hexdigest()
        container_client.get_blob_client(
            blob=f"{self.partition_key}/{hashed}.txt"
        ).upload_blob(self._content, overwrite=True)


class AIEnrichment(BaseModel):
    """Represents an AI enrichment entity associated with an RSS entry.

    Attributes:
        entry: The associated RSS entry.
        summary: AI-generated summary of the entry.
        grade_level: Flesch-Kincaid readability score.
        difficulty: Dale-Chall readability score.
        engagement_score: Engagement score for the entry.
        engagement_categories: List of engagement categories (e.g., 'Liked', 'Comment', 'Shared').
        embeddings: AI-generated embeddings as a numpy array; retrieved from Azure Blob Storage if not already cached.
        partition_key: Inherited partition key from the associated entry.
        row_key: Computed row key derived from the associated entry's id.
    """
    model_config = ConfigDict(
        populate_by_name=True, 
        from_attributes=True, 
        validate_assignment=True,
        arbitrary_types_allowed=True,
        extra="ignore"
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
        max_length=500,
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
    _embeddings: Optional[np.ndarray] = Field(
        default=None,
        exclude=True,
        description="Cached embeddings of the entry."
        )

    def model_post_init(self, __context):
        embeddings: np.ndarray = __context.get("data", {}).get("embeddings")
        if not all(embeddings, isinstance(embeddings, np.ndarray)):
            raise ValueError("Embeddings must be a numpy array.")
        self._embeddings = embeddings

    @computed_field(alias="Embeddings", include=False, description="AI generated embeddings")
    @property
    def embeddings(self) -> Optional[np.ndarray]:
        """Retrieve the AI-generated embeddings.

        Returns the embeddings numpy array from cache if available;
        otherwise, loads it from Azure Blob Storage.
        """
        if self._embeddings is None:
            self._embeddings = self._get_embeddings_blob()
        return self._embeddings

    @log_and_raise_error("Failed to save AI enrichment")
    def save(self) -> None:
        """
        Save the current AIEnrichment instance to Azure Table Storage.
        """
        if self._embeddings:
            self._persist_embeddings(self._embeddings)
        ai_enrichment_table_client.upsert_entity(self.model_dump(mode="json", by_alias=True))
    
    @log_and_raise_error("Failed to delete AI enrichment")
    def delete(self) -> None:
        """
        Delete the AIEnrichment instance from Azure Table Storage using its partition and row keys.
        """
        ai_enrichment_table_client.delete_entity(self.partition_key, self.row_key)

    @classmethod
    def create(cls, **kwargs) -> "AIEnrichment":
        """
        Create the AIEnrichment instance to Azure Table Storage.
        Validates the input data and saves the instance.
        Args:
            **kwargs: Keyword arguments containing the AI enrichment data.
        Returns:
            AIEnrichment: The created AIEnrichment instance.
        Raises:
            ValueError: If the data is invalid or cannot be created.
        """
        enrichment = cls.model_validate(dict(kwargs), strict=False)
        enrichment.save()
        return enrichment
    
    @log_and_return_default(default_value=None, message="Failed to retrieve embeddings blob")
    def _get_embeddings_blob(self) -> Optional[np.ndarray]:
        """
        Retrieve and load the embeddings numpy array from Azure Blob Storage.

        Loads the numpy array from a blob identified by the partition key and embeddings key,
        returning None if the blob is not available.
        """
        blob_bytes = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self.partition_key}/{self.row_key}.npy",
        )
        if blob_bytes:
            return np.load(io.BytesIO(blob_bytes))
        return None

    def _persist_embeddings(self, value: np.ndarray) -> None:
        """
        Persist the embeddings numpy array to Azure Blob Storage.
 
        Serializes the numpy array, computes its hash, caches the array, and uploads it to Azure Blob Storage.
        """
        buf = io.BytesIO()
        np.save(buf, value)
        buf.seek(0)
        bytes_data = buf.getvalue()
        hashed = xxhash.xxh64(bytes_data).hexdigest()
        container_client.get_blob_client(
            blob=f"{self.partition_key}/{hashed}.npy"
            ).upload_blob(bytes_data, overwrite=True)
