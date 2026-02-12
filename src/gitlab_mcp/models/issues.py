"""Issue models."""

from typing import Literal
from pydantic import Field, field_validator, field_serializer
from gitlab_mcp.models.base import BaseGitLabModel, relative_time, safe_str


class IssueSummary(BaseGitLabModel):
    """issue summary."""

    iid: int = Field(description="Issue number within the project")
    title: str
    description: str | None = ""
    state: Literal["opened", "closed"]
    author: str
    assignees: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    url: str = Field(alias="web_url")
    created: str = Field(alias="created_at")
    updated: str = Field(alias="updated_at")
    confidential: bool = False
    weight: int | None = None
    due_date: str | None = None
    milestone: str | None = None
    time_stats: dict | None = None
    related_mrs_count: int = Field(0, description="Number of related MRs (detail calls only)")

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, v):
        """Convert None to empty string."""
        return "" if v is None else v

    @field_validator("author", mode="before")
    @classmethod
    def extract_author(cls, v):
        """Extract username from author dict."""
        return v["username"] if isinstance(v, dict) else v

    @field_validator("assignees", mode="before")
    @classmethod
    def extract_assignees(cls, v):
        """Extract usernames from assignees list."""
        if not v:
            return []
        return [a["username"] for a in v] if isinstance(v[0], dict) else v

    @field_validator("milestone", mode="before")
    @classmethod
    def extract_milestone(cls, v):
        """Extract title from milestone dict."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v.get("title")
        if isinstance(v, str):
            return v
        # Handle any other type (like MagicMock in tests) as None
        return None

    @field_validator("time_stats", mode="before")
    @classmethod
    def extract_time_stats(cls, v):
        """Extract time tracking stats."""
        if v is None:
            return None
        if isinstance(v, dict):
            return {
                "time_estimate": v.get("time_estimate"),
                "total_time_spent": v.get("total_time_spent"),
                "human_time_estimate": v.get("human_time_estimate"),
                "human_total_time_spent": v.get("human_total_time_spent"),
            }
        # Handle any other type (like MagicMock in tests) as None
        return None

    @field_serializer("description")
    def serialize_description(self, v: str) -> str:
        """Clean null descriptions."""
        return safe_str(v)

    @field_serializer("created", "updated")
    def serialize_datetime(self, v: str) -> str:
        """Format as relative time."""
        return relative_time(v)


class IssueNote(BaseGitLabModel):
    """A comment/note on an issue."""

    id: int
    body: str
    author: str
    created: str = Field(alias="created_at")
    is_system: bool = Field(
        False,
        description="Whether this is a system-generated note",
        alias="system",
    )
    reactions: dict[str, int] = Field(
        default_factory=dict, description="Emoji reactions with counts", exclude=True
    )

    @field_validator("author", mode="before")
    @classmethod
    def extract_author(cls, v):
        """Extract username from author dict."""
        return v["username"] if isinstance(v, dict) else v

    @field_serializer("body")
    def serialize_body(self, v: str) -> str:
        """Clean null body."""
        return safe_str(v)

    @field_serializer("created")
    def serialize_datetime(self, v: str) -> str:
        """Format as relative time."""
        return relative_time(v)


class IssueLink(BaseGitLabModel):
    """Link between two issues."""

    source_issue: int
    target_issue: int
    link_type: str  # relates_to, blocks, is_blocked_by

    @field_validator("source_issue", "target_issue", mode="before")
    @classmethod
    def extract_issue_iid(cls, v):
        """Extract iid from issue dict."""
        return v["iid"] if isinstance(v, dict) else v
