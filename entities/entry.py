"""Module for RSS entry entity representation and persistence.

This module defines the Entry class, which models an RSS entry with properties such as title, link, content,
published date, updated date, author, and summary. The unique identifier is computed from the entry id using xxhash
and integrates with Azure Table Storage for create, update, delete, and serialization operations.
"""

from datetime import datetime
from typing import Optional, List
import os

import xxhash
from pydantic import BaseModel, Field, computed_field, HttpUrl, ConfigDict
import requests

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_return_default
from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)

ENTRY_TABLE_NAME = os.getenv("RSS_ENTRY_TABLE_NAME", "entries")
CONTAINER_NAME = os.getenv("RSS_ENTRY_CONTAINER_NAME", "entries")
AI_ENRICHMENT_TABLE_NAME = os.getenv("AI_ENRICHMENT_TABLE_NAME", "ai_enrichment")
entry_table_client = acf.get_instance().get_table_service_client().get_table_client(table_name=ENTRY_TABLE_NAME)
ai_enrichment_table_client = acf.get_instance().get_table_service_client().get_table_client(table_name=AI_ENRICHMENT_TABLE_NAME)
container_client = acf.get_instance().get_blob_service_client().get_container_client(container_name=CONTAINER_NAME)

class Entry(BaseModel):
    """Represents an RSS entry entity with properties including title, link, content, published and updated timestamps,
    author, and summary. The unique identifier (RowKey) is computed from the entry id using xxhash and is read-only.
    
    This model integrates with Azure Table Storage by mapping model fields to table entity properties via field aliases.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, validate_assignment=True)
    
    _partition_key: str = Field(default="entry", alias="PartitionKey")
    _row_key: Optional[str] = Field(default=None, alias="RowKey")
    title: str = Field(default="Untitled", min_length=1, max_length=200)
    id: str
    feed: str
    link: HttpUrl
    _content: Optional[str] = Field(default=None, alias="content")
    _content_cache: Optional[str] = None
    published: datetime = datetime(1970, 1, 1)
    author: Optional[str] = Field(default=None, min_length=2, max_length=50)
    summary: Optional[str] = Field(default=None, max_length=500)
    source: Optional[dict] = None

    @computed_field(alias="RowKey")
    @property
    def row_key(self) -> str:
        return xxhash.xxh64(self.id).hexdigest()

    # Added public computed property to access partition_key safely
    @computed_field(alias="PartitionKey")
    @property
    def partition_key(self) -> str:
        return self._partition_key

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
            self._content = xxhash.xxh64(text).hexdigest()
            self._content_cache = text
        return self._content_cache

    def __setattr__(self, name, value):
        if name == "content":
            hashed = xxhash.xxh64(value).hexdigest()
            object.__setattr__(self, "_content", hashed)
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
        """Retrieves the content blob from Azure Blob Storage.

        Returns:
            str: The content blob as a string.
        """
        blob = acf.get_instance().download_blob_content(
            container_client=container_client,
            blob_name=f"{self._partition_key}/{self._content}.txt",
        )
        return blob
    
    @log_and_return_default(default_value=None, message="Failed to retrieve content")
    def _get_content_http(self) -> Optional[str]:  # Renamed function
        """Retrieves the content from the entry's content URL.

        Returns:
            str: The content retrieved from the URL.
        """
        response = requests.get(self.link, timeout=10)
        return response.text if response.status_code == 200 else response.raise_for_status()

class AIEnrichment(BaseModel):
    """
    Represents an AI enrichment for an Entry object.
    Integrates with an AI service to generate additional insights.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, validate_assignment=True)
    entry: Entry
    ai_summary: Optional[str] = None
    fk_readability: Optional[float] = None  # Flesch-Kincaid readability score
    dc_readability: Optional[float] = None  # Dale-Chall readability score
    engagement_score: Optional[float] = None  # Engagement score
    engagement_categories: Optional[List[str]] = None  # Categories of engagement

    @computed_field(alias="PartitionKey")
    @property
    def partition_key(self) -> str:
        return self.entry.partition_key  # Using public property from Entry

    @computed_field(alias="RowKey")
    @property
    def row_key(self) -> str:
        return self.entry.row_key

    def enrich(self) -> str:
        """
        Enriches the associated Entry using AI and returns a summary.

        Returns:
            str: The AI-generated summary.
        """
        content = self.entry.content  # Retrieve content from the Entry.
        # ...integration with AI service to generate a summary...
        # For simulation, generate a placeholder summary based on content length.
        self.ai_summary = f"Summary (AI): {content[:75]}..." if content else "No content available."
        return self.ai_summary

    def save(self) -> None:
        ai_enrichment_table_client.upsert_entity(self.model_dump())
    
    @classmethod
    def create(cls, **kwargs) -> "AIEnrichment":
        enrichment = cls(**kwargs)
        ai_enrichment_table_client.upsert_entity(enrichment.model_dump())
        return enrichment

