"""Milestone models."""

from typing import Literal
from pydantic import Field, field_serializer
from gitlab_mcp.models.base import BaseGitLabModel, relative_time


class MilestoneSummary(BaseGitLabModel):
    """Milestone summary."""

    id: int
    title: str
    description: str = Field(default="", description="Milestone description")
    state: Literal["active", "closed"]
    due_date: str | None = Field(None, description="Due date (YYYY-MM-DD)")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    url: str = Field(description="Web URL", alias="web_url")
    created: str = Field(description="When created (relative)", alias="created_at")
    updated: str = Field(description="When last updated (relative)", alias="updated_at")

    @field_serializer("created", "updated")
    def serialize_datetime(self, v: str) -> str:
        """Format as relative time for AI consumption."""
        return relative_time(v)
