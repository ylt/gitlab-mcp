"""Release models."""

from datetime import datetime
from pydantic import Field, field_validator, field_serializer, computed_field
from gitlab_mcp.models.base import BaseGitLabModel, relative_time


class ReleaseSummary(BaseGitLabModel):
    """AI-optimized release summary."""

    tag_name: str = Field(description="Release tag (e.g., v1.0.0)")
    name: str | None = None
    description: str | None = None
    author: str | None = None
    created_at: datetime = Field(description="When created")
    released_at: datetime | None = Field(None, description="When released")

    @field_validator('author', mode='before')
    @classmethod
    def extract_author(cls, v):
        """Extract username from author dict."""
        if isinstance(v, dict):
            return v.get("username")
        return v

    @field_serializer('created_at')
    def serialize_created_at(self, v: datetime) -> str:
        """Format created_at as relative time."""
        return relative_time(v)

    @field_serializer('released_at')
    def serialize_released_at(self, v: datetime | None) -> str | None:
        """Format released_at as relative time."""
        return relative_time(v) if v else None
