"""Draft note models."""

from datetime import datetime
from pydantic import Field, field_validator, computed_field
from gitlab_mcp.models.base import BaseGitLabModel, relative_time


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


class DraftNoteDeleteResult(BaseGitLabModel):
    """Result of deleting a draft note."""

    deleted: bool = Field(description="True if draft note was deleted")
    draft_note_id: int = Field(description="ID of the deleted draft note")


class DraftNotePublishResult(BaseGitLabModel):
    """Result of publishing a draft note."""

    published: bool = Field(description="True if draft note was published")
    draft_note_id: int = Field(description="ID of the published draft note")


class BulkPublishDraftNotesResult(BaseGitLabModel):
    """Result of publishing all draft notes."""

    published_all: bool = Field(description="True if all draft notes were published")
    merge_request_iid: int = Field(description="MR IID")
