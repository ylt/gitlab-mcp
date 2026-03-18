"""Discussion and note models."""

from pydantic import Field
from pydantic import model_validator

from gitlab_mcp.models.base import (
    BaseGitLabModel,
    HtmlCommentFree,
    RelativeTime,
    RelativeTimeOptional,
    SafeString,
)


class NoteSummary(BaseGitLabModel):
    """Note/comment summary."""

    id: int = Field(description="Note ID")
    body: HtmlCommentFree = Field(description="Comment text")
    author: str = Field(description="Author username")
    created_at: RelativeTime = Field(description="When created (ISO timestamp)")
    updated_at: RelativeTimeOptional = Field(
        default=None, description="When last updated (ISO timestamp)"
    )
    system: bool = Field(default=False, description="True if this is a system-generated note")
    resolvable: bool | None = Field(default=False, description="True if this note can be resolved")
    resolved: bool | None = Field(default=False, description="True if this note is resolved")

    @model_validator(mode="before")
    @classmethod
    def flatten_author(cls, data):
        """Flatten nested author dict to username string."""
        if isinstance(data, dict):
            author = data.get("author")
            if isinstance(author, dict):
                data = dict(data)
                data["author"] = author.get("username", "unknown")
            return data
        author = getattr(data, "author", None)
        if isinstance(author, dict):
            return {
                "id": getattr(data, "id", None),
                "body": getattr(data, "body", ""),
                "author": author.get("username", "unknown"),
                "created_at": getattr(data, "created_at", ""),
                "updated_at": getattr(data, "updated_at", None),
                "system": getattr(data, "system", False),
                "resolvable": getattr(data, "resolvable", False),
                "resolved": getattr(data, "resolved", False),
            }
        return data


class NoteDetail(NoteSummary):
    """Full note with unstripped body for individual fetches."""

    body: SafeString = Field(description="Full comment text (unstripped)")


class DiscussionDetail(BaseGitLabModel):
    """Full discussion thread with unstripped note bodies."""

    id: str = Field(description="Discussion ID")
    notes: list[NoteDetail] = Field(
        default_factory=list, description="List of notes in discussion"
    )
    individual_note: bool = Field(default=False, description="True if single comment, not a thread")

    @classmethod
    def from_gitlab(cls, obj):
        """Transform GitLab Discussion object(s) to model instance(s)."""
        if isinstance(obj, list):
            return [cls.from_gitlab(item) for item in obj]

        notes_data = []
        if hasattr(obj, 'attributes') and 'notes' in obj.attributes:
            raw_notes = obj.attributes['notes']
            if isinstance(raw_notes, list):
                notes_data = raw_notes
            elif hasattr(raw_notes, 'list'):
                notes_data = [n.attributes for n in raw_notes.list()]
            else:
                notes_data = list(raw_notes)

        return cls.model_validate({
            'id': obj.id,
            'notes': notes_data,
            'individual_note': getattr(obj, 'individual_note', False),
        })


class DiscussionSummary(BaseGitLabModel):
    """Discussion thread summary.

    By default only shows note_count and the last note. Use
    include_all_notes=True on the tool to get every note.
    """

    id: str = Field(description="Discussion ID")
    note_count: int = Field(default=0, description="Total number of notes in discussion")
    notes: list[NoteSummary] = Field(
        default_factory=list, description="Notes (last note only by default, all if requested)"
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
            'note_count': len(notes_data),
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
