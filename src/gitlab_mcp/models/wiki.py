"""Wiki models."""

from typing import Literal, Any, Annotated
from pydantic import Field, field_validator, BeforeValidator, PlainSerializer
from gitlab_mcp.models.base import BaseGitLabModel, relative_time, safe_str, RelativeTimeOptional


def ensure_string(v: Any) -> str:
    """Convert None or any value to string.

    Pydantic validator to handle None or any value and convert to string.
    Used for content field which may be None from API.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


class WikiPageSummary(BaseGitLabModel):
    """wiki page summary (for list views)."""

    slug: str = Field(description="URL-safe page identifier")
    title: str
    format: Literal["markdown", "rdoc", "asciidoc"] = "markdown"
    created: RelativeTimeOptional = Field(None, alias="created_at", description="When created (relative)")
    updated: RelativeTimeOptional = Field(
        None, alias="updated_at", description="When last updated (relative)"
    )

    @field_validator("created", "updated", mode="before")
    @classmethod
    def extract_and_format_datetime(cls, v: Any) -> str | None:
        """Extract datetime value and format as relative time."""
        if v is None:
            return None
        # If already a string (relative time), pass through
        if isinstance(v, str):
            return v
        # Convert datetime object to relative time
        return relative_time(v)


class WikiPageDetail(BaseGitLabModel):
    """Wiki page with full content."""

    slug: str = Field(description="URL-safe page identifier")
    title: str
    content: Annotated[str, BeforeValidator(ensure_string), PlainSerializer(safe_str, return_type=str)]
    format: Literal["markdown", "rdoc", "asciidoc"] = "markdown"
    created: RelativeTimeOptional = Field(None, alias="created_at", description="When created (relative)")
    updated: RelativeTimeOptional = Field(
        None, alias="updated_at", description="When last updated (relative)"
    )

    @field_validator("created", "updated", mode="before")
    @classmethod
    def extract_and_format_datetime(cls, v: Any) -> str | None:
        """Extract datetime value and format as relative time."""
        if v is None:
            return None
        # If already a string (relative time), pass through
        if isinstance(v, str):
            return v
        # Convert datetime object to relative time
        return relative_time(v)


class WikiPageDeleteResult(BaseGitLabModel):
    """Result of deleting a wiki page."""

    deleted: bool = Field(description="Whether the page was successfully deleted")
    slug: str = Field(description="Slug of the deleted page")


class WikiAttachmentResult(BaseGitLabModel):
    """Result of uploading a wiki attachment."""

    markdown: str = Field(description="Markdown link to the attachment")
    url: str = Field(description="URL of the uploaded file")
    alt: str = Field(description="Alt text for the attachment")
    filename: str = Field(description="Name of the uploaded file")
    size_bytes: int = Field(description="Size of the file in bytes")
