"""Draft notes tools for merge requests."""

from typing import cast
from gitlab.v4.objects import ProjectMergeRequest, ProjectMergeRequestDraftNote
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import DraftNoteSummary
from gitlab_mcp.utils.serialization import serialize_pydantic


@mcp.tool(
    annotations={
        "title": "List Draft Notes",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def list_draft_notes(project_id: str, mr_iid: int) -> list[DraftNoteSummary]:
    """List all draft notes on a merge request.

    Draft notes are unpublished comments that only you can see.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        mr_iid: Merge request number within the project
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    draft_notes = mr.draft_notes.list()
    return [
        DraftNoteSummary.model_validate(n, from_attributes=True) for n in draft_notes
    ]


@mcp.tool(
    annotations={
        "title": "Get Draft Note",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def get_draft_note(project_id: str, mr_iid: int, draft_note_id: int) -> DraftNoteSummary:
    """Get a specific draft note.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        draft_note_id: Draft note ID
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    note = cast(ProjectMergeRequestDraftNote, mr.draft_notes.get(draft_note_id))
    return DraftNoteSummary.model_validate(note, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Create Draft Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    data: dict[str, str | int] = {"body": note}
    if in_reply_to_discussion_id:
        data["in_reply_to_discussion_id"] = in_reply_to_discussion_id
    draft_note = cast(ProjectMergeRequestDraftNote, mr.draft_notes.create(data))
    return DraftNoteSummary.model_validate(draft_note, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Update Draft Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    draft_note = cast(ProjectMergeRequestDraftNote, mr.draft_notes.get(draft_note_id))
    draft_note.body = note
    draft_note.save()
    return DraftNoteSummary.model_validate(draft_note, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Delete Draft Note",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_draft_note(project_id: str, mr_iid: int, draft_note_id: int) -> dict[str, bool | int]:
    """Delete a draft note.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        draft_note_id: Draft note ID to delete
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    mr.draft_notes.delete(draft_note_id)
    return {"deleted": True, "draft_note_id": draft_note_id}


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
) -> dict[str, bool | int]:
    """Publish a single draft note as a comment.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        draft_note_id: Draft note ID to publish
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    draft_note = mr.draft_notes.get(draft_note_id)
    draft_note.publish()
    return {"published": True, "draft_note_id": draft_note_id}


@mcp.tool(
    annotations={
        "title": "Publish All Draft Notes",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def bulk_publish_draft_notes(project_id: str, mr_iid: int) -> dict[str, bool | int]:
    """Publish all draft notes on a merge request as comments.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    mr.publish_all_draft_notes()
    return {"published_all": True, "merge_request_iid": mr_iid}
