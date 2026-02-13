"""Issue models."""

from typing import Literal
from pydantic import Field, field_validator, field_serializer
from gitlab_mcp.models.base import BaseGitLabModel, relative_time, safe_str


def format_seconds(seconds: int) -> str:
    """Convert seconds to human-readable format."""
    if seconds == 0:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    parts: list[str] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    return "".join(parts) if parts else "0m"


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

    id: int
    type: str = Field(alias="link_type")
    target_project_id: int
    target_issue_iid: int


class IssueDeleteResult(BaseGitLabModel):
    """Result of deleting an issue."""

    status: str = Field(description="Deletion status (always 'deleted')")
    issue_iid: int = Field(description="Issue number that was deleted")


class IssueLinkDeleteResult(BaseGitLabModel):
    """Result of deleting an issue link."""

    status: str = Field(description="Deletion status (always 'deleted')")
    link_id: int = Field(description="Link ID that was deleted")


class RelatedMergeRequest(BaseGitLabModel):
    """A merge request related to an issue."""

    id: int = Field(description="Merge request ID")
    iid: int = Field(description="Merge request number within project")
    title: str = Field(description="MR title")
    state: str = Field(description="MR state (opened, closed, merged, locked)")
    url: str = Field(alias="web_url", description="Web URL to view MR")


class IssueTimeStats(BaseGitLabModel):
    """Time tracking statistics for an issue."""

    time_estimate: str = Field(description="Time estimate in human-readable format (e.g., '2h30m')")
    time_estimate_seconds: int = Field(description="Time estimate in seconds")
    total_time_spent: str = Field(description="Total time spent in human-readable format")
    total_time_spent_seconds: int = Field(description="Total time spent in seconds")
    human_time_estimate: str | None = Field(
        None, description="Human-readable time estimate from GitLab"
    )
    human_total_time_spent: str | None = Field(
        None, description="Human-readable total time spent from GitLab"
    )

    @field_serializer("time_estimate")
    def serialize_time_estimate(self, v: str | int) -> str:
        """Convert time estimate seconds to human-readable format."""
        if isinstance(v, str):
            return v
        return format_seconds(v)

    @field_serializer("total_time_spent")
    def serialize_total_time_spent(self, v: str | int) -> str:
        """Convert total time spent seconds to human-readable format."""
        if isinstance(v, str):
            return v
        return format_seconds(v)
