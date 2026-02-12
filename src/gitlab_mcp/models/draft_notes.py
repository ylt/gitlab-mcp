"""Draft note models."""

from datetime import datetime
from pydantic import Field, field_validator, computed_field
from gitlab_mcp.models.base import BaseGitLabModel, relative_time, safe_str


class DraftNoteSummary(BaseGitLabModel):
    """AI-optimized draft note summary."""

    id: int = Field(description="Draft note ID")
    body: str = Field(description="Draft note body text")
    in_reply_to_discussion_id: str | None = Field(
        default=None, description="Discussion ID if this is a reply"
    )
    created_at: datetime = Field(description="When created")

    @field_validator("body", mode="before")
    @classmethod
    def extract_body(cls, v) -> str:
        """Extract body, ensuring non-null string."""
        if v is None or v == "":
            return ""
        return v if isinstance(v, str) else str(v)

    @computed_field
    @property
    def created(self) -> str:
        """When created (relative time)."""
        return relative_time(self.created_at)
