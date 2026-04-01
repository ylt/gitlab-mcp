"""Issue models."""

from typing import Literal
from pydantic import Field, field_validator
from gitlab_mcp.models.base import BaseGitLabModel, RelativeTime, SafeString
from gitlab_mcp.models.misc import UserRef


class IssueSummary(BaseGitLabModel):
    """issue summary."""

    iid: int = Field(description="Issue number within the project")
    title: str
    description: SafeString = ""
    state: Literal["opened", "closed"]
    author: UserRef
    assignees: list[UserRef] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    url: str = Field(alias="web_url")
    created: RelativeTime = Field(alias="created_at")
    updated: RelativeTime = Field(alias="updated_at")
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


class IssueNote(BaseGitLabModel):
    """A comment/note on an issue."""

    id: int
    body: SafeString
    author: UserRef
    created: RelativeTime = Field(alias="created_at")
    is_system: bool = Field(
        False,
        description="Whether this is a system-generated note",
        alias="system",
    )
    reactions: dict[str, int] = Field(
        default_factory=dict, description="Emoji reactions with counts", exclude=True
    )


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

    time_estimate: int = Field(0, description="Time estimate in seconds")
    total_time_spent: int = Field(0, description="Total time spent in seconds")
    human_time_estimate: str | None = Field(
        None, description="Human-readable time estimate from GitLab"
    )
    human_total_time_spent: str | None = Field(
        None, description="Human-readable total time spent from GitLab"
    )
