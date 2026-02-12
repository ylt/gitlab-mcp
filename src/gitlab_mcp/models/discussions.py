"""Discussion and note models."""

from pydantic import Field, field_validator, field_serializer
from gitlab_mcp.models.base import BaseGitLabModel, relative_time, safe_str


class NoteSummary(BaseGitLabModel):
    """Note/comment summary."""

    id: int = Field(description="Note ID")
    body: str = Field(description="Comment text")
    author: str = Field(description="Username of author")
    created_at: str = Field(description="When created (ISO timestamp)")
    updated_at: str | None = Field(default=None, description="When last updated (ISO timestamp)")
    resolved: bool = Field(default=False, description="True if this note resolves a discussion")

    @field_validator("author", mode="before")
    @classmethod
    def extract_author(cls, v):
        """Extract username from author dict."""
        return v["username"] if isinstance(v, dict) else v

    @field_serializer("body")
    def serialize_body(self, v: str) -> str:
        """Clean null body."""
        return safe_str(v)

    @field_serializer("created_at")
    def serialize_created(self, v: str) -> str:
        """Format as relative time."""
        return relative_time(v) if v else "unknown"

    @field_serializer("updated_at")
    def serialize_updated(self, v: str | None) -> str | None:
        """Format as relative time."""
        return relative_time(v) if v else None


class DiscussionSummary(BaseGitLabModel):
    """Discussion thread summary."""

    id: str = Field(description="Discussion ID")
    notes: list[NoteSummary] = Field(
        default_factory=list, description="List of notes in discussion"
    )
    created_at: str = Field(description="When created (ISO timestamp)")
    updated_at: str | None = Field(default=None, description="When last updated (ISO timestamp)")
    individual_note: bool = Field(default=False, description="True if single comment, not a thread")

    @field_validator("notes", mode="before")
    @classmethod
    def extract_notes(cls, v):
        """Extract notes list from API response."""
        if not v:
            return []
        # Convert raw note dicts to NoteSummary models
        return [NoteSummary.model_validate(note, from_attributes=True) for note in v]

    @field_serializer("created_at")
    def serialize_created(self, v: str) -> str:
        """Format as relative time."""
        return relative_time(v) if v else "unknown"

    @field_serializer("updated_at")
    def serialize_updated(self, v: str | None) -> str | None:
        """Format as relative time."""
        return relative_time(v) if v else None
