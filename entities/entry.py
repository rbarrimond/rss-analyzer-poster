"""Module for RSS entry entity representation and persistence.

This module defines the Entry and AIEnrichment classes.
Entry models an RSS entry with properties such as title, link, and content.
The content is retrieved using a caching mechanism, hashed via xxhash,
and stored in Azure Blob Storage. AIEnrichment handles AI-based enhancements,
including summaries, readability scores, engagement data, and embeddings kept as numpy arrays.
"""

from datetime import datetime
from typing import Optional, Literal, Set
import os
import io

import xxhash
from azure.data.tables import TableClient
from azure.storage.blob import ContainerClient
from pydantic import BaseModel, Field, computed_field, HttpUrl, ConfigDict
import requests
import numpy as np

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_return_default, retry_on_failure
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__, os.getenv("LOG_LEVEL", "INFO"))

entry_table_client: TableClient = acf.get_instance().get_table_service_client().get_table_client(
    table_name=os.getenv("RSS_ENTRY_TABLE_NAME", "entries")
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
        partition_key: Partition key for Azure Table Storage.
        title: Title of the entry.
        id: Internal unique identifier of the entry.
        feed_key: RowKey of the feed (16 hex characters).
        link: URL link to the entry.
        published: Published date of the entry.
        author: Author of the entry.
        summary: Summary of the entry.
        source: Source information for the entry.
        content: Content of the entry; retrieved from Azure Blob Storage if cached, otherwise via HTTP.
        row_key: Computed row key derived from the entry's id using xxhash.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, validate_assignment=True)
    
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
    content_key: Optional[str] = Field(
        default=None,
        alias="ContentKey",
        min_length=16,
        max_length=16,
        pattern=r"^[a-f0-9]{16}$",
        exclude=True,
        description="Key for the content blob in Azure Blob Storage."
        )
    content_cache: Optional[str] = Field(
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
        """Retrieve the content of the entry.

        Uses cached content if available. If not, attempts to load from Azure Blob Storage;
        if that fails, fetches via HTTP, computes a hash for the text, caches it, and then returns it.
        """
        if not self.content_cache:
            text = self._get_content_blob()
            if not text:
                text = self._get_content_http()  # Attempt to download from the link
            if not text:
                raise ValueError("Content is not available.")
            # Set _content to the hash of the text and cache the text
            self.content_key = xxhash.xxh64(text).hexdigest()
            self.content_cache = text
        return self._content_cache

    def __setattr__(self, name, value):
        """
        Customize attribute assignment.

        For the 'content' attribute, computes its hash, caches the content, and uploads it to Azure Blob Storage
        under a path based on the partition key and the computed content hash.
        Standard assignment is performed for other attributes.
        """
        if name == "content":
            hashed = xxhash.xxh64(value).hexdigest()
            object.__setattr__(self, "_content_key", hashed)
            object.__setattr__(self, "_content_cache", value)
            container_client.get_blob_client(blob=f"{self.partition_key}/{hashed}.txt").upload_blob(value, overwrite=True)
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
        # Filter out unknown keys using updated model_fields
        valid_kwargs = {k: v for k, v in kwargs.items() if k in Entry.model_fields.keys()}
        entry = cls(**valid_kwargs)
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
        entry_table_client.delete_entity(self.partition_key, self.row_key)

    @log_and_return_default(default_value=None, message="Failed to retrieve content blob")
    def _get_content_blob(self) -> Optional[str]:
        """
        Retrieve the content blob from Azure Blob Storage.

        The blob is identified by a combination of the partition key and the content key.
        """
        blob = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self.partition_key}/{self._content_key}.txt",
        )
        return blob
    
    @log_and_return_default(default_value=None, message="Failed to retrieve content")
    @retry_on_failure(retries=3, delay=2000)
    def _get_content_http(self) -> Optional[str]:
        """
        Retrieve the content via HTTP from the entry's link.

        Attempts to download the entry content with a timeout. If the response status is 200, returns the text;
        otherwise, raises an HTTP error.
        """
        response = requests.get(self.link, timeout=10)
        return response.text if response.status_code == 200 else response.raise_for_status()

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
        arbitrary_types_allowed=True
        )
    
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
    engagement_categories: Optional[Set[Literal['Liked', 'Comment', 'Shared']]] = Field(
        default=None,
        alias="EngagementCategories",
        max_items=3,
        min_items=1,
        description="Categories of engagement"
        )
    embeddings_key: Optional[str] = Field(
        default=None,
        alias="EmbeddingsKey",
        min_length=16,
        max_length=16,
        pattern=r"^[a-f0-9]{16}$",
        description="Key for the embeddings blob in Azure Blob Storage."
        )
    embeddings_cache: Optional[np.ndarray] = Field(
        default=None,
        exclude=True,
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
        """Retrieve the AI-generated embeddings.

        Returns the embeddings numpy array from cache if available;
        otherwise, loads it from Azure Blob Storage.
        """
        if self.embeddings_cache is None:
            data = self._get_embeddings_blob()
            if data is None:
                raise ValueError("Embeddings not available.")
            object.__setattr__(self, "embeddings_cache", data)
        return self.embeddings_cache

    def __setattr__(self, name, value):
        """
        Customize attribute assignment for embeddings.

        When setting 'embeddings', the numpy array is serialized, hashed, cached, and
        uploaded to Azure Blob Storage under a path based on the partition key and computed hash.
        Standard assignment is performed for all other attributes.
        """
        if name == "embeddings":
            buf = io.BytesIO()
            np.save(buf, value)
            buf.seek(0)
            bytes_data = buf.getvalue()
            hashed = xxhash.xxh64(bytes_data).hexdigest()
            object.__setattr__(self, "embeddings_key", hashed)
            object.__setattr__(self, "embeddings_cache", value)
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
        # Filter out unknown keys using updated model_fields
        valid_kwargs = {k: v for k, v in kwargs.items() if k in AIEnrichment.model_fields.keys()}
        enrichment = cls(**valid_kwargs)
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

        Loads the numpy array from a blob identified by the partition key and embeddings key,
        returning None if the blob is not available.
        """
        blob_bytes = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self.partition_key}/{self._embeddings_key}.npy",
        )
        if blob_bytes:
            return np.load(io.BytesIO(blob_bytes))
        return None
