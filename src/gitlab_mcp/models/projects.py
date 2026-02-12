"""Project models."""

from pydantic import Field, field_validator, field_serializer, computed_field
from gitlab_mcp.models.base import BaseGitLabModel, relative_time


class ProjectSummary(BaseGitLabModel):
    """project summary."""

    id: int
    path_with_namespace: str = Field(alias="path")
    name: str
    description: str | None = None
    web_url: str = Field(alias="url")
    default_branch: str = "main"
    visibility: str
    created_at: str = Field(alias="created")
    star_count: int = 0
    forks_count: int = Field(default=0, alias="fork_count")
    last_activity_at: str = "unknown"
    open_issues_count: int = 0

    @field_serializer('description')
    def serialize_description(self, v: str | None) -> str:
        """Convert None to empty string for output."""
        return "" if v is None else v

    @field_validator('default_branch', mode='before')
    @classmethod
    def default_branch_fallback(cls, v):
        """Provide fallback if None."""
        return v if v else "main"

    @field_validator('created_at', mode='before')
    @classmethod
    def format_created(cls, v):
        """Convert datetime to relative time."""
        return relative_time(v) if v else "unknown"

    @field_validator('last_activity_at', mode='before')
    @classmethod
    def format_last_activity(cls, v):
        """Convert datetime to relative time or unknown."""
        return relative_time(v) if v else "unknown"

    @computed_field
    @property
    def is_active(self) -> bool:
        """True if project had activity in last 30 days."""
        if not self.last_activity_at or self.last_activity_at == "unknown":
            return False
        from datetime import datetime, timedelta
        try:
            activity_date = datetime.fromisoformat(self.last_activity_at.replace('Z', '+00:00'))
            return datetime.now(activity_date.tzinfo) - activity_date < timedelta(days=30)
        except (ValueError, AttributeError, TypeError):
            return False

    @computed_field
    @property
    def is_public(self) -> bool:
        """True if project is publicly visible."""
        return self.visibility == "public"


class ProjectMember(BaseGitLabModel):
    """Project member info."""

    username: str
    name: str
    access_level: int | str
    expires_at: str | None = None

    @field_validator('access_level', mode='before')
    @classmethod
    def convert_access_level(cls, v):
        """Convert numeric access level codes to strings."""
        access_levels = {
            10: "guest",
            20: "reporter",
            30: "developer",
            40: "maintainer",
            50: "owner",
        }
        if isinstance(v, int):
            return access_levels.get(v, str(v))
        return v
