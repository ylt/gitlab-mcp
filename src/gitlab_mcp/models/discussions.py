"""Discussion and note models."""

from pydantic import Field
from gitlab_mcp.models.base import (
    BaseGitLabModel,
    HtmlCommentFree,
    RelativeTime,
    RelativeTimeOptional,
)
from gitlab_mcp.models.misc import UserRef


class NoteSummary(BaseGitLabModel):
    """Note/comment summary."""

    id: int = Field(description="Note ID")
    body: HtmlCommentFree = Field(description="Comment text")
    author: UserRef = Field(description="Author user reference")
    created_at: RelativeTime = Field(description="When created (ISO timestamp)")
    updated_at: RelativeTimeOptional = Field(
        default=None, description="When last updated (ISO timestamp)"
    )
    resolved: bool = Field(default=False, description="True if this note resolves a discussion")


class DiscussionSummary(BaseGitLabModel):
    """Discussion thread summary."""

    id: str = Field(description="Discussion ID")
    notes: list[NoteSummary] = Field(
        default_factory=list, description="List of notes in discussion"
    )
    individual_note: bool = Field(default=False, description="True if single comment, not a thread")

    @classmethod
    def from_gitlab(cls, obj):
        """Transform GitLab Discussion object(s) to model instance(s)."""
        # Handle list of discussions
        if isinstance(obj, list):
            return [cls.from_gitlab(item) for item in obj]

        # Extract notes from raw attributes (already fetched in API response)
        notes_data = []
        if hasattr(obj, 'attributes') and 'notes' in obj.attributes:
            raw_notes = obj.attributes['notes']
            if isinstance(raw_notes, list):
                notes_data = raw_notes
            elif hasattr(raw_notes, 'list'):
                # python-gitlab may wrap notes in a manager object
                notes_data = [n.attributes for n in raw_notes.list()]
            else:
                notes_data = list(raw_notes)

        return cls.model_validate({
            'id': obj.id,
            'notes': notes_data,
            'individual_note': getattr(obj, 'individual_note', False),
        })


class NoteDeleteResult(BaseGitLabModel):
    """Result of deleting a note."""

    deleted: bool = Field(description="True if note was deleted")
    note_id: int = Field(description="ID of the deleted note")
    merge_request_iid: int | None = Field(default=None, description="MR IID if applicable")
    discussion_id: str | None = Field(default=None, description="Discussion ID if applicable")


class DiscussionNoteDeleteResult(BaseGitLabModel):
    """Result of deleting a discussion note/reply."""

    deleted: bool = Field(description="True if note was deleted")
    note_id: int = Field(description="ID of the deleted note")
    discussion_id: str = Field(description="Discussion ID")
    merge_request_iid: int = Field(description="MR IID")
