"""Module for RSS entry entity representation and persistence.

This module defines the Entry and AIEnrichment classes. Entry models an RSS
entry with properties such as title, link, and content. The content is cached,
hashed via xxhash, and stored in Azure Blob Storage. AIEnrichment handles
AI-based enhancements like summaries, readability scores, engagement data, and
embeddings.
"""

from functools import cached_property, lru_cache
import io
import os
import threading
from datetime import datetime
from typing import Any, Literal, Optional, Set

import numpy as np
import requests
import xxhash
from pydantic import (BaseModel, ConfigDict, Field, HttpUrl, computed_field,
                      field_validator, PrivateAttr)

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_raise_error, log_and_return_default, log_execution_time, retry_on_failure, ensure_cleanup
from utils.logger import LoggerFactory
from utils.parser import normalize_html, html_to_markdown, parse_date, truncate_markdown

MAX_SUMMARY_SENTENCES = 20
MAX_SUMMARY_CHARACTERS = 2000

RSS_ENTRY_CONTAINER_NAME = os.getenv("RSS_ENTRIES_CONTAINER_NAME")
RSS_ENTRY_TABLE_NAME = os.getenv("RSS_ENTRIES_TABLE_NAME")

logger = LoggerFactory.get_logger(__name__)

# Define a module-level constant for the sentinel value
NULL_CONTENT = "\ue000"  # Unicode private use character for missing content


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
            "Tags",
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
    tags: list[str] = Field(
        default=None,
        alias="Tags",
        description="List of tags associated with the entry."
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

    # Private attributes
    _content_cache: Optional[str] = PrivateAttr(
        default=None)  # Cache for fetched content
    _http_fetch_lock: threading.Lock = PrivateAttr(
        default_factory=threading.Lock)
    _recursion_guard: threading.local = PrivateAttr(
        default_factory=threading.local)

    # Validators
    @field_validator("summary", mode="before")
    @classmethod
    def clean_and_truncate_summary(cls, v):
        """
        Clean and truncate the summary while preserving HTML structure.

        Args:
            v (str): The summary text to clean and truncate.

        Returns:
            str: The cleaned and truncated summary, or None if the input is empty.
        """
        if not v:
            return None
        v = normalize_html(v)
        v = html_to_markdown(v)
        v = truncate_markdown(v, MAX_SUMMARY_SENTENCES, MAX_SUMMARY_CHARACTERS)
        logger.debug("Summary cleaned and truncated to %d characters.", len(v))
        return v

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

        Raises:
            ValueError: If the input cannot be parsed into a valid datetime.
        """
        parsed_date = parse_date(v)
        if parsed_date is None:
            raise ValueError(f"Invalid date format for 'published': {v}")
        return parsed_date

    # Computed Fields
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

    @computed_field(alias="Content",
                    description="Content of the entry, retrieved from Azure Blob Storage or via HTTP if not cached.")
    @cached_property
    def content(self) -> Optional[str]:
        """
        Retrieve the content of the entry.

        If the content is not already cached, it attempts to fetch it from Azure Blob Storage or via HTTP.

        Returns:
            Optional[str]: The content of the entry, or NULL_CONTENT if not available.
        """
        return self.fetch_content()

    # Fetch Content
    @ensure_cleanup(lambda self: setattr(self._recursion_guard, "active", False))
    def fetch_content(self) -> Optional[str]:
        """
        Fetch the content of the entry from Blob Storage or HTTP.

        This method attempts to fetch the content from Azure Blob Storage first.
        If the content is not available in Blob Storage, it falls back to fetching via HTTP.

        Returns:
            Optional[str]: The fetched content, or NULL_CONTENT if not available.
        """
        # if getattr(self._recursion_guard, "active", False):
        #     logger.warning("Recursion detected in fetch_content for entry %s/%s.",
        #                  self.partition_key, self.row_key)
        #     return NULL_CONTENT  # Prevent recursion

        # self._recursion_guard.active = True  # Set the recursion guard
        # Fetch content from Blob Storage
        content = self._fetch_content_from_blob()
        if content:
            self._content_cache = content
            return content

        # Fallback to HTTP fetch
        logger.warning(
            "Content not available in blob storage. Attempting to retrieve from HTTP.")
        content = self._fetch_content_from_http()
        if content:
            self._content_cache = content
            return content

        # Content not available
        logger.warning("Content not available in blob storage or HTTP.")
        return NULL_CONTENT

    @log_execution_time()
    @ensure_cleanup(lambda self: setattr(self._recursion_guard, "active", False))
    @log_and_return_default(default_value=None, message="Failed to retrieve content from HTTP")
    def _fetch_content_from_http(self) -> Optional[str]:
        """
        Retrieve the content via HTTP from the entry's link.

        Attempts to download the entry content with a timeout. If the response status is 200, returns the text;
        otherwise, raises an HTTP error.

        This method is thread-safe to prevent simultaneous HTTP fetches for the same entry.
        """
        # if getattr(self._recursion_guard, "active", False):
        #     logger.warning("Recursion detected in _fetch_content_from_http for entry %s/%s.",
        #                  self.partition_key, self.row_key)
        #     return None  # Prevent recursion

        # self._recursion_guard.active = True  # Set the recursion guard
        with self._http_fetch_lock:  # Use the private thread lock
            logger.debug("Retrieving content from HTTP link: %s", self.link)

            response = requests.get(self.link, timeout=10)
            if response.status_code == 200:
                logger.debug("Content retrieved successfully from HTTP link.")
                norm_html = normalize_html(response.text)
                markdown = html_to_markdown(norm_html)
                logger.debug(
                    "Content converted to markdown. Length %d characters.", len(markdown))
                return markdown
            else:
                logger.warning(
                    "Failed to retrieve content from HTTP link. Status code: %d", response.status_code)
                logger.debug("Response content: %s", response.text)
                response.raise_for_status()

    @log_and_return_default(default_value=None, message="Failed to retrieve content blob")
    def _fetch_content_from_blob(self) -> Optional[str]:
        """
        Retrieve the content blob from Azure Blob Storage.

        The blob is identified by a combination of the partition key and the content key.

        Returns:
            Optional[str]: The content as a string, or None if the blob is not available.
        """
        blob_path = f"{self.partition_key}/{self.row_key}_content.md"
        logger.debug("Retrieving content blob: %s", blob_path)

        return acf.get_instance().download_blob_content(
            container_name=RSS_ENTRY_CONTAINER_NAME,
            blob_name=blob_path,
        )

    # Save Content
    @log_and_raise_error("Failed to persist content")
    @retry_on_failure(retries=1, delay=2000)
    def _save_content_to_blob(self, entry_content: str) -> None:
        """
        Persist the content to Azure Blob Storage.

        Uploads the content to Azure Blob Storage under a path based on the partition key
        and the row key.

        Args:
            entry_content (str): The content to persist.
        """
        if not entry_content:
            raise ValueError("Content is not available to persist.")

        upload_result = acf.get_instance().upload_blob_content(
            container_name=RSS_ENTRY_CONTAINER_NAME,
            blob_name=f"{self.partition_key}/{self.row_key}_content.md",
            content=entry_content,
        )

        logger.debug("Content %s/%s_content.txt persisted to blob storage with result %s.",
                     self.partition_key, self.row_key, upload_result)

    # Cache Management
    def get_cached_content(self) -> Optional[str]:
        """
        Retrieve the cached content of the entry.

        Returns:
            Optional[str]: The cached content, or None if not cached.
        """
        return self._content_cache

    # Persistence
    @log_and_raise_error("Failed to save entry")
    def save(self) -> None:
        """
        Save or update the Entry instance in Azure Table Storage.

        Fetches the content if not already cached and persists it to Blob Storage.
        """
        content = self.get_cached_content() or self.fetch_content()
        if not content or content == NULL_CONTENT:
            raise ValueError("Content is not available.")

        # Persist the content and update the entity in Azure Table Storage
        self._save_content_to_blob(content)
        acf.get_instance().table_upsert_entity(
            self.model_dump(mode="json", by_alias=True))

    @log_and_raise_error("Failed to delete entry")
    def delete(self) -> None:
        """
        Delete the Entry instance from Azure Table Storage.

        Removes the corresponding entity record using its partition and row keys.
        """
        acf.get_instance().delete_blob(container_name=RSS_ENTRY_CONTAINER_NAME,
                                       blob_name=f"{self.partition_key}/{self.row_key}_content.txt")
        acf.get_instance().table_delete_entity(RSS_ENTRY_TABLE_NAME,
                                               self.model_dump(
                                                   mode="json", by_alias=True)
                                               )
        logger.debug("Entry %s/%s deleted from blob storage.",
                     self.partition_key, self.row_key)

    # @field_serializer("content", mode="wrap")
    # def serialize_content(self, field, value, info):
    #     """
    #     Customize the serialization of the 'content' field.

    #     Exclude the field when dumping to a dictionary but include it when serializing to JSON.
    #     """
    #     _ = field
    #     if info.mode == "dict":
    #         return None  # Exclude from dict serialization
    #     return value  # Include in JSON serialization


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
        alias="PartitionKey",
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Partition key of the associated entry (alphanumeric, dash, underscore only) to ensure a valid blob path."
    )
    row_key: str = Field(
        alias="RowKey",
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
        max_length=3,
        min_length=1,
        description="Categories of engagement"
    )

    # Private attributes
    _recursion_guard: threading.local = PrivateAttr(
        default_factory=threading.local)

    # @computed_field(alias="Embeddings", description="Cached embeddings of the entry.")
    @cached_property
    def embeddings(self) -> Optional[np.ndarray]:
        """
        Retrieve the embeddings numpy array from Azure Blob Storage.

        If the embeddings are not already cached, fetch them from Azure Blob Storage.

        Returns:
            Optional[np.ndarray]: The embeddings numpy array, or None if not available.
        """
        return self._fetch_embeddings_from_blob

    @ensure_cleanup(lambda self: setattr(self._recursion_guard, "active", False))
    def _fetch_embeddings_from_blob(self) -> Optional[np.ndarray]:
        """
        Retrieve and load the embeddings numpy array from Azure Blob Storage.

        Returns:
            Optional[np.ndarray]: The embeddings numpy array, or None if the blob is not available.
        """
        if getattr(self._recursion_guard, "active", False):
            logger.error("Recursion detected in _fetch_embeddings_from_blob for AI enrichment %s/%s.",
                         self.partition_key, self.row_key)
            return None  # Prevent recursion

        self._recursion_guard.active = True  # Set the recursion guard
        blob_bytes = acf.get_instance().download_blob_content(
            container_name=RSS_ENTRY_CONTAINER_NAME,
            blob_name=f"{self.partition_key}/{self.row_key}_embeddings.npy",
        )
        if blob_bytes is None:
            return None

        embeddings = np.load(io.BytesIO(blob_bytes), allow_pickle=True)
        logger.debug("Embeddings %s/%s_embeddings.npy loaded from blob storage.",
                     self.partition_key, self.row_key)
        return embeddings

    @log_and_raise_error("Failed to save AI enrichment")
    def save(self, save_embeddings: np.ndarray = None) -> None:
        """
        Save the current AIEnrichment instance to Azure Table Storage.

        If embeddings are provided, they are persisted to Azure Blob Storage.
        """
        embeddings = save_embeddings if save_embeddings is not None else self.embeddings
        if embeddings is None:
            raise ValueError("Embeddings are not available.")

        self._save_embeddings_to_blob(embeddings)
        acf.get_instance().table_upsert_entity(table_name=RSS_ENTRY_TABLE_NAME,
                                               entity=self.model_dump(mode="json", by_alias=True))
        logger.debug("AI enrichment %s/%s saved.",
                     self.partition_key, self.row_key)

    @log_and_raise_error("Failed to delete AI enrichment")
    def delete(self) -> None:
        """
        Delete the AIEnrichment instance from Azure Table Storage using its partition and row keys.

        Also deletes the associated embeddings blob from Azure Blob Storage.
        """
        acf.get_instance().table_delete_entity(table_name=RSS_ENTRY_TABLE_NAME,
                                               entity=self.model_dump(mode="json", by_alias=True))
        acf.get_instance().delete_blob(container_name=RSS_ENTRY_CONTAINER_NAME,
                                       blob_name=f"{self.partition_key}/{self.row_key}_embeddings.npy")
        logger.debug("AI enrichment %s/%s deleted.",
                     self.partition_key, self.row_key)

    @log_and_raise_error("Failed to persist embeddings")
    @retry_on_failure(retries=1, delay=2000)
    def _save_embeddings_to_blob(self, embeddings: np.ndarray) -> None:
        """
        Persist the embeddings numpy array to Azure Blob Storage.

        Serializes the numpy array using np.save and uploads it to Azure Blob Storage.
        """
        if embeddings is None:
            raise ValueError("Embeddings are not available to persist.")

        # Serialize the embeddings to a BytesIO buffer
        buffer = io.BytesIO()
        np.save(buffer, embeddings)
        buffer.seek(0)  # Reset the buffer position to the beginning

        # Upload the serialized embeddings to Azure Blob Storage
        result = acf.get_instance().upload_blob_content(
            container_name=RSS_ENTRY_CONTAINER_NAME,
            blob_name=f"{self.partition_key}/{self.row_key}_embeddings.npy",
            content=buffer.read(),
        )

        logger.debug("Embeddings %s/%s_embeddings.npy persisted to blob storage with result %s.",
                     self.partition_key, self.row_key, result)
