"""Miscellaneous models for namespaces, users, iterations."""

from typing import Literal
from pydantic import Field, field_validator
from gitlab_mcp.models.base import (
    BaseGitLabModel,
    RelativeTime,
    RelativeTimeOptional,
    SafeString,
    safe_str,
)


class NamespaceSummary(BaseGitLabModel):
    """namespace summary."""

    id: int
    name: str
    path: str
    full_path: str
    kind: Literal["user", "group"]
    description: str | None = None


class UserRef(BaseGitLabModel):
    """Slim user reference for embedding in other models."""

    id: int = Field(0, description="User ID")
    username: str = Field(description="Username (login)")
    name: str | None = Field(None, description="Display name")


class UserSummary(BaseGitLabModel):
    """user summary."""

    id: int
    username: str
    name: str
    state: str | None = None
    last_active: RelativeTimeOptional = Field(None, exclude=True, alias="last_activity_on")


class EventSummary(BaseGitLabModel):
    """event/activity summary."""

    id: int
    action: str | None = Field(None, exclude=True, alias="action_name")
    target_type: str | None = None
    target_title: SafeString = None
    author: UserRef | None = None
    created: RelativeTime = Field(exclude=True, alias="created_at")


class IterationSummary(BaseGitLabModel):
    """iteration/sprint summary."""

    id: int
    title: str
    description: SafeString = None
    state: str
    start_date: str | None = None
    due_date: str | None = None
    url: str = Field(alias="web_url")
    created: RelativeTime = Field(exclude=True, alias="created_at")


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
