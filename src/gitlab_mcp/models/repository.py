"""Repository and file models."""

from typing import Literal
from pydantic import Field, field_validator, computed_field
from gitlab_mcp.models.base import BaseGitLabModel, relative_time


class FileSummary(BaseGitLabModel):
    """File or directory info."""

    path: str
    name: str
    type: Literal["file", "directory"]
    size: int | None = None
    encoding: str | None = None
    last_modified: str | None = None
    last_commit_message: str | None = None

    @field_validator('type', mode='before')
    @classmethod
    def normalize_type(cls, v):
        """Convert 'tree' to 'directory' for consistency."""
        if v == "tree":
            return "directory"
        return v


class FileContents(BaseGitLabModel):
    """File contents with metadata."""

    path: str
    content: str
    size: int
    last_commit: str = Field(description="Short SHA of last commit")
    syntax_language: str | None = Field(None, description="Language hint for syntax highlighting (from file extension)")
    truncated: bool = Field(False, description="Indicates if content was truncated")


class CommitSummary(BaseGitLabModel):
    """commit summary."""

    id: str = Field(exclude=True)  # Raw full SHA
    title: str = Field(exclude=True)  # Raw commit title
    author_name: str  # Keep as-is from API
    created_at: str = Field(exclude=True)  # ISO datetime
    parent_ids: list[str] | None = Field(None, exclude=True)  # Raw parent SHAs
    stats: dict | None = Field(None, exclude=True)  # Raw stats dict

    @computed_field
    @property
    def sha(self) -> str:
        """Short SHA (first 8 chars)."""
        return self.id[:8]

    @computed_field
    @property
    def message(self) -> str:
        """First line of commit message."""
        return self.title

    @computed_field
    @property
    def author(self) -> str:
        """Commit author name."""
        return self.author_name

    @computed_field
    @property
    def created(self) -> str:
        """When created (relative time)."""
        return relative_time(self.created_at)

    @computed_field
    @property
    def parent_sha(self) -> str | None:
        """Short SHA of parent commit (first 8 chars)."""
        if self.parent_ids and len(self.parent_ids) > 0:
            return self.parent_ids[0][:8]
        return None

    @computed_field
    @property
    def files_changed(self) -> int | None:
        """Number of files changed (if stats fetched)."""
        if self.stats:
            return self.stats.get("total")
        return None

    @computed_field
    @property
    def insertions(self) -> int | None:
        """Lines added (if stats fetched)."""
        if self.stats:
            return self.stats.get("additions")
        return None

    @computed_field
    @property
    def deletions(self) -> int | None:
        """Lines deleted (if stats fetched)."""
        if self.stats:
            return self.stats.get("deletions")
        return None


class BranchSummary(BaseGitLabModel):
    """Branch info."""

    name: str
    commit: dict | str  # Raw commit object or SHA
    protected: bool = False
    ahead_count: int | None = Field(None, description="Commits ahead of default branch")
    behind_count: int | None = Field(None, description="Commits behind default branch")
    last_activity_at: str | None = Field(None, exclude=True)  # ISO datetime

    @field_validator('commit', mode='before')
    @classmethod
    def extract_commit_object(cls, v):
        """Extract commit dict or normalize string."""
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            return {"id": v}
        return v

    @computed_field
    @property
    def commit_sha(self) -> str:
        """Short SHA of HEAD commit."""
        if isinstance(self.commit, dict):
            return self.commit.get("id", "")[:8]
        return ""

    @computed_field
    @property
    def last_activity(self) -> str | None:
        """Relative time of last commit."""
        if self.last_activity_at:
            return relative_time(self.last_activity_at)
        return None


class DiffSummary(BaseGitLabModel):
    """Summary of changes between two refs."""

    from_ref: str
    to_ref: str
    files_changed: int
    insertions: int
    deletions: int
