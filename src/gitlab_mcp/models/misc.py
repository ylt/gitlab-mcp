"""Miscellaneous models for namespaces, users, iterations."""

from typing import Literal
from pydantic import Field, field_serializer, computed_field, field_validator
from gitlab_mcp.models.base import BaseGitLabModel, relative_time, safe_str


class NamespaceSummary(BaseGitLabModel):
    """namespace summary."""

    id: int
    name: str
    path: str
    full_path: str
    kind: Literal["user", "group"]
    description: str | None = None


class UserSummary(BaseGitLabModel):
    """user summary."""

    id: int
    username: str
    name: str
    state: str | None = None
    last_activity_on: str | None = Field(None, exclude=True)

    @computed_field
    @property
    def last_active(self) -> str | None:
        """Last activity (relative time)."""
        return relative_time(self.last_activity_on) if self.last_activity_on else None


class EventSummary(BaseGitLabModel):
    """event/activity summary."""

    id: int
    action_name: str | None = Field(None, exclude=True)
    target_type: str | None = None
    target_title: str | None = None
    author: str | None = None
    created_at: str = Field(exclude=True)

    @field_validator("target_title", mode="before")
    @classmethod
    def clean_target_title(cls, v):
        """Clean null target titles."""
        return safe_str(v)

    @field_validator("author", mode="before")
    @classmethod
    def extract_author(cls, v):
        """Extract username from author dict."""
        if isinstance(v, dict):
            return v.get("username")
        return v

    @computed_field
    @property
    def action(self) -> str | None:
        """Action name."""
        return self.action_name

    @computed_field
    @property
    def created(self) -> str:
        """When created (relative time)."""
        return relative_time(self.created_at)


class IterationSummary(BaseGitLabModel):
    """iteration/sprint summary."""

    id: int
    title: str
    description: str | None = None
    state: str
    start_date: str | None = None
    due_date: str | None = None
    web_url: str
    created_at: str = Field(exclude=True)

    @field_serializer("description")
    def serialize_description(self, v: str | None) -> str:
        """Clean description (None → empty string)."""
        return safe_str(v)

    @computed_field
    @property
    def url(self) -> str:
        """Web URL to view iteration."""
        return self.web_url

    @computed_field
    @property
    def created(self) -> str:
        """When created (relative time)."""
        return relative_time(self.created_at)


class NamespaceVerification(BaseGitLabModel):
    """Result of verifying a namespace."""

    exists: bool = Field(description="Whether the namespace exists")
    id: int | None = Field(None, description="Namespace ID if found")
    name: str | None = Field(None, description="Namespace name if found")
    path: str | None = Field(None, description="Namespace path if found")
    full_path: str | None = Field(None, description="Full path if found")
    kind: Literal["user", "group"] | None = Field(None, description="Namespace kind if found")
    error: str | None = Field(None, description="Error message if not found")
    suggestions: list[dict] | None = Field(None, description="Similar namespaces if requested")
