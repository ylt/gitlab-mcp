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


class MilestoneDeleteResult(BaseGitLabModel):
    """Result of deleting a milestone."""

    success: bool = Field(description="Whether deletion was successful")
    message: str = Field(description="Deletion confirmation message")


class MilestoneBurndownEvent(BaseGitLabModel):
    """Milestone burndown chart event."""

    id: int = Field(description="Event ID")
    created_at: str = Field(description="When the event was created")
    weight: int | None = Field(None, description="Issue weight")
    user_id: int | None = Field(None, description="User ID who triggered event")
    issue_id: int | None = Field(None, description="Issue ID associated with event")


class MilestonePromoteResult(BaseGitLabModel):
    """Result of promoting a project milestone to group milestone."""

    id: int
    title: str
    description: str = Field(default="", description="Milestone description")
    state: Literal["active", "closed"]
    due_date: str | None = Field(None, description="Due date (YYYY-MM-DD)")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    url: str = Field(description="Web URL", alias="web_url")
    created: str = Field(description="When created (relative)", alias="created_at")
    updated: str = Field(description="When last updated (relative)", alias="updated_at")
    promoted: bool = Field(description="Whether milestone was promoted to group level")

    @field_serializer("created", "updated")
    def serialize_datetime(self, v: str) -> str:
        """Format as relative time for AI consumption."""
        return relative_time(v)
