"""Post entity for a blog post.
This module defines the Post class which represents a blog post.
It includes:
- A 'draft_date' indicating when the post was created.
- A computed 'partition_key' based on 'draft_date' in YYYY-MM format.
- A computed 'row_key' that is a hash of the title, content, and draft_date.
"""
from datetime import datetime, timezone
import os
from typing import List, Literal, Optional

import markdown
import xxhash
from azure.data.tables import TableClient
from pydantic import (BaseModel, ConfigDict, Field, computed_field, field_validator)

from utils.azclients import AzureClientFactory as acf
from utils.decorators import log_and_raise_error

post_table_client: TableClient = acf.get_instance().get_table_service_client().get_table_client(
    table_name=os.getenv("POST_TABLE_NAME", "posts")
)
post_table_client.create_table_if_not_exists()

class Post(BaseModel):
    """Represents a blog post with optional AI enrichment.
    
    Attributes:
        title (Optional[str]): The title of the blog post.
        draft_date (datetime): The datetime when the post was drafted.
        keywords (Optional[List[str]]): Keywords extracted from the post.
        content (Optional[str]): The post content in Markdown format.
        draft_status (Optional[List[Literal['Draft', 'Edited', 'Approved', 'Posted']]]): The current draft state.
    
    Computed Properties:
        partition_key (str): A string in "YYYY-MM" format derived from the draft_date.
        row_key (str): A unique hash computed from the title, content, and draft_date.
    """
    model_config = ConfigDict(populate_by_name=True,
                              from_attributes=True,
                              validate_assignment=True)

    title: Optional[str] = Field(
        default=None,
        alias="Title",
        min_length=1,
        max_length=100,
        description="Title of the blog post"
        )
    draft_date: datetime = Field(
        default=datetime.now(timezone.utc),
        alias="DraftDate",
        description="Draft date of the blog post"
        )
    keywords: Optional[List[str]] = Field(
        default=None,
        alias="Keywords",
        min_length=1,
        max_length=10,
        description="Keywords extracted from the post content"
        )
    content: Optional[str] = Field(
        default=None,
        alias="Content",
        min_length=1,
        max_length=10000,
        description="Content of the blog post in Markdown format"
        )
    draft_status: Optional[List[Literal['Draft', 'Edited', 'Approved', 'Posted']]] = Field(
        default=None,
        alias="DraftStatus",
        min_length=1,
        max_length=1,
        description="Draft status of the blog post"
        )

    @log_and_raise_error(message="Error in Post entity. Content not valid markdown.")
    @field_validator("content")
    @classmethod
    def validate_markdown_content(cls, v) -> Optional[str]:
        """Validates that the content is valid Markdown.

        This method converts the Markdown to HTML to perform a basic validation.
        
        Args:
            v (str): The Markdown content.
            
        Returns:
            Optional[str]: The HTML representation of the content if valid, otherwise None.
            
        Raises:
            ValueError: Propagates any conversion error.
        """
        # Attempt to convert markdown to HTML as a basic validation
        return markdown.markdown(v) if v else None

    @log_and_raise_error(message="Error in Post entity. Draft date not valid.")
    @computed_field(alias="PartitionKey", description="Partition key based on draft date in YYYY-MM format")
    @property
    def partition_key(self) -> str:
        """Computes the partition key from the draft_date.

        Returns:
            str: The draft_date formatted as 'YYYY-MM'.
            
        Raises:
            AttributeError: If draft_date is not a valid datetime object.
        """
        if isinstance(self.draft_date, datetime):
            return self.draft_date.strftime("%Y-%m")
        raise AttributeError("draft_date must be a datetime object")

    @log_and_raise_error(message="Error in Post entity. Row key not valid.")
    @computed_field(alias="RowKey", description="Row key computed as hash of original drafted post")
    @property
    def row_key(self) -> str:
        """Computes a unique row key based on the title, content, and draft_date.

        Returns:
            str: A hash value representing the unique key for the post.
        """
        if all(self.title, self.content, isinstance(self.draft_date, datetime)):
            return xxhash.xxh64(f"{self.title}_{self.content}_{self.draft_date.isoformat()}").hexdigest()
        raise AttributeError("title, content, and draft_date must be provided")
    
    def save(self) -> None:
        """Saves the post entity to the Azure Table Storage posts table."""
        post_table_client.upsert_entity(self.model_dump())
    
    def delete(self) -> None:
        """Deletes the Post instance from Azure Table Storage."""
        post_table_client.delete_entity(self.partition_key, self.row_key)
    
    @classmethod
    def create(cls, **kwargs) -> "Post":
        """Creates and persists a Post instance in Azure Table Storage."""
        post = cls(**kwargs)
        post.save()
        return post
