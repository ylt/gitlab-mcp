"""Draft notes tools for merge requests."""

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import (
    DraftNoteSummary,
    DraftNoteDeleteResult,
    DraftNotePublishResult,
    BulkPublishDraftNotesResult,
)


@mcp.tool(
    annotations={
        "title": "List Draft Notes",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_draft_notes(project_id: str, mr_iid: int) -> list[DraftNoteSummary]:
    """List all draft notes on a merge request.

    Draft notes are unpublished comments that only you can see.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        mr_iid: Merge request number within the project
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    draft_notes = mr.draft_notes.list()
    return [DraftNoteSummary.from_gitlab(n) for n in draft_notes]


@mcp.tool(
    annotations={
        "title": "Get Draft Note",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_draft_note(project_id: str, mr_iid: int, draft_note_id: int) -> DraftNoteSummary:
    """Get a specific draft note.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        draft_note_id: Draft note ID
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    note = mr.draft_notes.get(draft_note_id)
    return DraftNoteSummary.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Create Draft Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_draft_note(
    project_id: str,
    mr_iid: int,
    note: str,
    in_reply_to_discussion_id: int | None = None,
) -> DraftNoteSummary:
    """Create a new draft note on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        note: Draft note text (markdown supported)
        in_reply_to_discussion_id: Optional discussion ID to reply to
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    data: dict[str, str | int] = {"body": note}
    if in_reply_to_discussion_id:
        data["in_reply_to_discussion_id"] = in_reply_to_discussion_id
    draft_note = mr.draft_notes.create(data)
    return DraftNoteSummary.from_gitlab(draft_note)


@mcp.tool(
    annotations={
        "title": "Update Draft Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_draft_note(
    project_id: str,
    mr_iid: int,
    draft_note_id: int,
    note: str,
) -> DraftNoteSummary:
    """Update an existing draft note.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        draft_note_id: Draft note ID to update
        note: New draft note text (markdown supported)
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    draft_note = mr.draft_notes.get(draft_note_id)
    draft_note.body = note
    draft_note.save()
    return DraftNoteSummary.from_gitlab(draft_note)


@mcp.tool(
    annotations={
        "title": "Delete Draft Note",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_draft_note(project_id: str, mr_iid: int, draft_note_id: int) -> DraftNoteDeleteResult:
    """Delete a draft note.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        draft_note_id: Draft note ID to delete
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    mr.draft_notes.delete(draft_note_id)
    return DraftNoteDeleteResult.model_validate({"deleted": True, "draft_note_id": draft_note_id})


@mcp.tool(
    annotations={
        "title": "Publish Draft Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def publish_draft_note(
    project_id: str,
    mr_iid: int,
    draft_note_id: int,
) -> DraftNotePublishResult:
    """Publish a single draft note as a comment.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        draft_note_id: Draft note ID to publish
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    draft_note = mr.draft_notes.get(draft_note_id)
    draft_note.publish()
    return DraftNotePublishResult.model_validate({"published": True, "draft_note_id": draft_note_id})


@mcp.tool(
    annotations={
        "title": "Publish All Draft Notes",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def bulk_publish_draft_notes(project_id: str, mr_iid: int) -> BulkPublishDraftNotesResult:
    """Publish all draft notes on a merge request as comments.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    mr.publish_all_draft_notes()
    return BulkPublishDraftNotesResult.model_validate({"published_all": True, "merge_request_iid": mr_iid})
