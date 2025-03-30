"""Module for RSS entry entity representation and persistence.

This module defines the Entry class, which models an RSS entry with properties such as title, link, content,
published date, updated date, author, and summary. The unique identifier is computed from the entry id using xxhash
and integrates with Azure Table Storage for create, update, delete, and serialization operations.
"""

from datetime import datetime
from typing import Optional, List, Literal
import os
import io

import xxhash
from pydantic import BaseModel, Field, computed_field, HttpUrl, ConfigDict
import requests
import numpy as np

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_return_default, retry_on_failure

ENTRY_TABLE_NAME = os.getenv("RSS_ENTRY_TABLE_NAME", "entries")
CONTAINER_NAME = os.getenv("RSS_ENTRY_CONTAINER_NAME", "entries")
AI_ENRICHMENT_TABLE_NAME = os.getenv("AI_ENRICHMENT_TABLE_NAME", "ai_enrichment")
entry_table_client = acf.get_instance().get_table_service_client().get_table_client(table_name=ENTRY_TABLE_NAME)
ai_enrichment_table_client = acf.get_instance().get_table_service_client().get_table_client(table_name=AI_ENRICHMENT_TABLE_NAME)
container_client = acf.get_instance().get_blob_service_client().get_container_client(container_name=CONTAINER_NAME)

class Entry(BaseModel):
    """Represents an RSS entry entity.

    Public Attributes:
        partition_key (str): Partition key for Azure Table Storage.
        title (str): Title of the entry.
        id (str): Internal unique identifier of the entry.
        feed_key (str): RowKey of the feed (16 hex characters).
        link (HttpUrl): URL link to the entry.
        published (datetime): Published date of the entry.
        author (Optional[str]): Author of the entry.
        summary (Optional[str]): Summary of the entry.
        source (Optional[dict]): Source information for the entry.
        content (Optional[str]): Content of the entry (retrieved via blob or HTTP).
        row_key (str): Computed row key derived from the entry's id using xxhash.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, validate_assignment=True)
    
    partition_key: str = Field(
        default="entry",
        alias="PartitionKey",
        regex=r"^[a-zA-Z0-9_-]+$",
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
        regex=r"^[a-f0-9]{16}$",
        description="RowKey of the feed to which this entry belongs."
        )
    link: HttpUrl = Field(
        alias="Link",
        description="URL link to the entry. Must be a valid HTTP or HTTPS URL."
        )
    _content_key: Optional[str] = Field(
        default=None,
        alias="ContentKey",
        min_length=16,
        max_length=16,
        regex=r"^[a-f0-9]{16}$",
        description="Key for the content blob in Azure Blob Storage."
        )
    _content_cache: Optional[str] = Field(
        default=None,
        description="Cached content of the entry."
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
        min_length=2,
        max_length=50
        )
    summary: Optional[str] = Field(
        default=None,
        alias="Summary",
        description="Summary of the entry.",
        min_length=2,
        max_length=500
        )
    source: Optional[dict] = Field(
        default=None,
        alias="Source",
        description="Source of the entry."
        )

    @computed_field(alias="RowKey", description="RowKey of the entry in Azure Table Storage.")
    @property
    def row_key(self) -> str:
        """Return the computed row key derived from the entry's id."""
        return xxhash.xxh64(self.id).hexdigest()

    @log_and_return_default(default_value=None, message="Failed to retrieve content")
    @property
    def content(self) -> Optional[str]:
        """Returns the content of the entry.
        
        Returns:
            Optional[str]: The content of the entry as a string.
        """
        if not self._content_cache:
            text = self._get_content_blob()
            if not text:
                text = self._get_content_http()  # Attempt to download from the link
            if not text:
                raise ValueError("Content is not available.")
            # Set _content to the hash of the text and cache the text
            self._content_key = xxhash.xxh64(text).hexdigest()
            self._content_cache = text
        return self._content_cache

    def __setattr__(self, name, value):
        """
        Override __setattr__ to customize assignment handling for the 'content' attribute.
        
        When 'content' is set, its value is hashed and cached, and the full text is uploaded to Azure Blob Storage.
        For all other attributes, default assignment is used.
        """
        if name == "content":
            hashed = xxhash.xxh64(value).hexdigest()
            object.__setattr__(self, "_content_key", hashed)
            object.__setattr__(self, "_content_cache", value)
            container_client.get_blob_client(blob=f"{self._partition_key}/{hashed}.txt").upload_blob(value, overwrite=True)
        else:
            super().__setattr__(name, value)

    @classmethod
    def create(cls, **kwargs) -> "Entry":
        """Creates and persists an Entry instance in Azure Table Storage.

        Args:
            **kwargs: Keyword arguments corresponding to Entry properties.

        Returns:
            Entry: The created and persisted Entry instance.
        """
        entry = cls(**kwargs)
        entry_table_client.upsert_entity(entry.model_dump())
        return entry

    def save(self) -> None:
        """Saves (or updates) the Entry instance in Azure Table Storage.

        Serializes the current state of the Entry and updates the entity record in the storage.
        """
        entry_table_client.upsert_entity(self.model_dump())

    def delete(self) -> None:
        """Deletes the Entry instance from Azure Table Storage.

        Removes the corresponding entity record using its partition and row keys.
        """
        entry_table_client.delete_entity(self._partition_key, self.row_key)

    @log_and_return_default(default_value=None, message="Failed to retrieve content blob")
    def _get_content_blob(self) -> Optional[str]:
        """
        Retrieve the content blob from Azure Blob Storage.
        
        Returns:
            Optional[str]: The downloaded content as a string if available, otherwise None.
        """
        blob = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self._partition_key}/{self._content_key}.txt",
        )
        return blob
    
    @log_and_return_default(default_value=None, message="Failed to retrieve content")
    @retry_on_failure(retries=3, delay=2000)
    def _get_content_http(self) -> Optional[str]:
        """
        Retrieve the content via HTTP from the provided content URL.
        
        Returns:
            Optional[str]: The content retrieved from the URL if successful, otherwise raises an HTTP error.
        """
        response = requests.get(self.link, timeout=10)
        return response.text if response.status_code == 200 else response.raise_for_status()

class AIEnrichment(BaseModel):
    """Represents an AI enrichment entity associated with an RSS entry.

    Public Attributes:
        entry (Entry): The associated RSS entry.
        summary (Optional[str]): AI generated summary.
        grade_level (Optional[float]): Flesch-Kincaid readability score (0 = easiest, 12 = high school, 15+ = complex academic text).
        difficulty (Optional[float]): Dale-Chall readability score (4.9 = easy, 8.0 = difficult, 10+ = very difficult).
        engagement_score (Optional[float]): Engagement score for the entry.
        engagement_categories (Optional[List[Literal['Liked', 'Comment', 'Shared']]]): Categories of engagement.
        embeddings (Optional[np.ndarray]): AI-generated embeddings (retrieved from blob storage).
        partition_key (str): Inherited partition key from the associated entry.
        row_key (str): Computed row key based on the associated entry's id.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, validate_assignment=True)
    
    entry: Entry
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
    engagement_categories: Optional[List[Literal['Liked', 'Comment', 'Shared']]] = Field(
        default=None,
        alias="EngagementCategories",
        max_items=3,
        min_items=1,
        unique_items=True,
        description="Categories of engagement"
        )
    _embeddings_key: Optional[str] = Field(
        default=None,
        alias="EmbeddingsKey",
        min_length=16,
        max_length=16,
        regex=r"^[a-f0-9]{16}$",
        description="Key for the embeddings blob in Azure Blob Storage."
        )
    _embeddings_cache: Optional[np.ndarray] = Field(
        default=None,
        description="Cached embeddings of the entry."
        )

    @computed_field(alias="PartitionKey")
    @property
    def partition_key(self) -> str:
        """Return the partition key of the associated entry."""
        return self.entry.partition_key

    @computed_field(alias="RowKey")
    @property
    def row_key(self) -> str:
        """Return the row key of the associated entry."""
        return self.entry.row_key

    @log_and_return_default(default_value=None, message="Failed to retrieve embeddings")
    @property
    def embeddings(self) -> Optional[np.ndarray]:
        """Returns the embeddings of the entry."""
        if self._embeddings_cache is None:
            data = self._get_embeddings_blob()
            if data is None:
                raise ValueError("Embeddings not available.")
            object.__setattr__(self, "_embeddings_cache", data)
        return self._embeddings_cache

    def __setattr__(self, name, value):
        """
        Override __setattr__ to handle assignment for the 'embeddings' property.
        
        When 'embeddings' is set, the numpy array is saved to a bytes buffer,
        hashed, cached, and then uploaded to Azure Blob Storage.
        """
        if name == "embeddings":
            buf = io.BytesIO()
            np.save(buf, value)
            buf.seek(0)
            bytes_data = buf.getvalue()
            hashed = xxhash.xxh64(bytes_data).hexdigest()
            object.__setattr__(self, "_embeddings_key", hashed)
            object.__setattr__(self, "_embeddings_cache", value)
            container_client.get_blob_client(
                blob=f"{self.partition_key}/{hashed}.npy").upload_blob(bytes_data, overwrite=True)
        else:
            super().__setattr__(name, value)

    def save(self) -> None:
        """
        Save the current AIEnrichment instance to Azure Table Storage.
        """
        ai_enrichment_table_client.upsert_entity(self.model_dump())
    
    @classmethod
    def create(cls, **kwargs) -> "AIEnrichment":
        """
        Create and persist a new AIEnrichment instance in Azure Table Storage.

        Args:
            **kwargs: Keyword arguments corresponding to AIEnrichment properties.

        Returns:
            AIEnrichment: The created and persisted instance.
        """
        enrichment = cls(**kwargs)
        ai_enrichment_table_client.upsert_entity(enrichment.model_dump())
        return enrichment

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
            Optional[np.ndarray]: The embeddings array if successfully retrieved, otherwise None.
        """
        blob_bytes = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self.partition_key}/{self._embeddings_key}.npy",
        )
        if blob_bytes:
            return np.load(io.BytesIO(blob_bytes))
        return None

