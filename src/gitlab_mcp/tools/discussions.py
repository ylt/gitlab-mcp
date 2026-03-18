"""Discussion and note tools for merge requests and issues."""

import logging
from typing import Any

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import (
    DiscussionSummary,
    NoteSummary,
    NoteDeleteResult,
    DiscussionNoteDeleteResult,
)
from gitlab_mcp.models.discussions import DiscussionDetail
from gitlab_mcp.utils.pagination import paginate

logger = logging.getLogger(__name__)


_MAX_BODY_PREVIEW = 500


def _truncate_note(note: NoteSummary) -> NoteSummary:
    """Truncate note body for preview."""
    if note.body and len(note.body) > _MAX_BODY_PREVIEW:
        note.body = note.body[:_MAX_BODY_PREVIEW] + "\n\n[... truncated — use get_mr_discussion for full content]"
    return note


def _filter_discussions(
    discussions: list[DiscussionSummary],
    include_system: bool,
    state: str = "all",
    include_all_notes: bool = False,
) -> list[DiscussionSummary]:
    """Filter discussions by system notes, resolution state, and collapse notes."""
    result = []
    for d in discussions:
        notes = d.notes

        if not include_system:
            notes = [n for n in notes if not n.system]

        if state == "unresolved":
            if all(n.resolved for n in notes if not n.system):
                continue
        elif state == "resolved":
            if not all(n.resolved for n in notes if not n.system):
                continue

        if not notes:
            continue

        d.note_count = len(notes)
        if include_all_notes:
            d.notes = notes
        elif len(notes) == 1:
            d.notes = [_truncate_note(notes[0])]
        else:
            skipped = len(notes) - 2
            placeholder = NoteSummary.model_validate({
                "id": 0,
                "body": f"[... {skipped} note(s) skipped — use get_mr_discussion for full thread]",
                "author": "—",
                "created_at": "—",
                "system": False,
                "resolved": False,
            })
            d.notes = [_truncate_note(notes[0]), placeholder, _truncate_note(notes[-1])]
        result.append(d)
    return result


@mcp.tool(annotations={"title": "MR Discussions", "readOnlyHint": True, "openWorldHint": True})
def mr_discussions(
    project_id: str,
    mr_iid: int,
    per_page: int = 20,
    include_system: bool = False,
    state: str = "all",
    include_all_notes: bool = False,
    raw: bool = False,
) -> list[DiscussionSummary] | list[DiscussionDetail]:
    """List discussions/threads on a merge request.

    By default shows only the last note per thread with a note_count.
    Note bodies are cleaned (HTML comments stripped, <details> blocks
    collapsed) and system notes are excluded. Use raw=True for full
    unstripped markdown. To fetch a single discussion with full content,
    use get_mr_discussion instead.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        mr_iid: Merge request number
        per_page: Items per page (default 20, max 100)
        include_system: Include system-generated notes (default false)
        state: Filter by resolution: "all", "unresolved", or "resolved"
        include_all_notes: Show all notes per thread (default false, shows last only)
        raw: Return full unstripped markdown bodies (default false)
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    discussions = paginate(mr.discussions, per_page=per_page)
    if raw:
        return DiscussionDetail.from_gitlab(discussions)
    result = DiscussionSummary.from_gitlab(discussions)
    return _filter_discussions(result, include_system, state, include_all_notes)


@mcp.tool(annotations={"title": "Issue Discussions", "readOnlyHint": True, "openWorldHint": True})
def list_issue_discussions(
    project_id: str,
    issue_iid: int,
    per_page: int = 20,
    include_system: bool = False,
    state: str = "all",
    include_all_notes: bool = False,
    raw: bool = False,
) -> list[DiscussionSummary] | list[DiscussionDetail]:
    """List discussions/threads on an issue.

    By default shows only the last note per thread with a note_count.
    Note bodies are cleaned and system notes are excluded.
    Use raw=True for full unstripped markdown.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        per_page: Items per page (default 20, max 100)
        include_system: Include system-generated notes (default false)
        state: Filter by resolution: "all", "unresolved", or "resolved"
        include_all_notes: Show all notes per thread (default false, shows last only)
        raw: Return full unstripped markdown bodies (default false)
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    discussions = paginate(issue.discussions, per_page=per_page)
    if raw:
        return DiscussionDetail.from_gitlab(discussions)
    result = DiscussionSummary.from_gitlab(discussions)
    return _filter_discussions(result, include_system, state, include_all_notes)


@mcp.tool(annotations={"title": "Get MR Discussion", "readOnlyHint": True, "openWorldHint": True})
def get_mr_discussion(
    project_id: str,
    mr_iid: int,
    discussion_id: str,
) -> DiscussionDetail:
    """Get a single discussion thread with full unstripped note bodies.

    Use this to see the complete content of notes that were collapsed
    in the mr_discussions listing.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        mr_iid: Merge request number
        discussion_id: Discussion ID
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    discussion = mr.discussions.get(discussion_id)
    return DiscussionDetail.from_gitlab(discussion)


@mcp.tool(
    annotations={
        "title": "Start Thread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_merge_request_thread(
    project_id: str,
    mr_iid: int,
    body: str,
    position: dict | None = None,
) -> DiscussionSummary:
    """Create a new discussion thread on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        body: Comment text (markdown supported)
        position: Optional position dict with keys:
            - base_sha: base commit SHA
            - start_sha: start commit SHA (for multi-commit comments)
            - head_sha: head commit SHA
            - old_path: file path in base version
            - new_path: file path in head version
            - old_line: line number in base version
            - new_line: line number in head version
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)

    data: dict[str, Any] = {"body": body}
    if position:
        data["position"] = position

    discussion = mr.discussions.create(data)
    return DiscussionSummary.from_gitlab(discussion)


@mcp.tool(
    annotations={
        "title": "Resolve Thread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def resolve_merge_request_thread(
    project_id: str,
    mr_iid: int,
    discussion_id: str,
    resolved: bool = True,
) -> DiscussionSummary:
    """Resolve or unresolve a discussion thread on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        discussion_id: Discussion ID
        resolved: True to resolve, False to unresolve
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    discussion = mr.discussions.get(discussion_id)

    discussion.resolved = resolved
    discussion.save()

    # Refresh to get updated details
    discussion = mr.discussions.get(discussion_id)
    return DiscussionSummary.from_gitlab(discussion)


@mcp.tool(
    annotations={
        "title": "Add Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_merge_request_note(
    project_id: str,
    mr_iid: int,
    body: str,
) -> NoteSummary:
    """Add a comment/note to a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        body: Comment text (markdown supported)
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    note = mr.notes.create({"body": body})
    return NoteSummary.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Edit Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_merge_request_note(
    project_id: str,
    mr_iid: int,
    note_id: int,
    body: str,
) -> NoteSummary:
    """Edit a comment/note on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        note_id: Note ID to edit
        body: Updated comment text (markdown supported)
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    note = mr.notes.get(note_id, lazy=True)

    note.body = body
    note.save()
    return NoteSummary.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Delete Comment",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_merge_request_note(
    project_id: str,
    mr_iid: int,
    note_id: int,
) -> NoteDeleteResult:
    """Delete a comment/note from a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        note_id: Note ID to delete
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)

    logger.warning(f"Deleting note {note_id} from merge request !{mr_iid} in project {project_id}")
    mr.notes.delete(note_id)

    return NoteDeleteResult.model_validate({
        "deleted": True,
        "note_id": note_id,
        "merge_request_iid": mr_iid,
    })


@mcp.tool(
    annotations={
        "title": "Add Issue Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_issue_note(
    project_id: str,
    issue_iid: int,
    body: str,
) -> NoteSummary:
    """Add a comment/note to an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        body: Comment text (markdown supported)
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    note = issue.notes.create({"body": body})
    return NoteSummary.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Edit Issue Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_issue_note(
    project_id: str,
    issue_iid: int,
    note_id: int,
    body: str,
) -> NoteSummary:
    """Edit a comment/note on an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        note_id: Note ID to edit
        body: Updated comment text (markdown supported)
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    note = issue.notes.get(note_id, lazy=True)

    note.body = body
    note.save()
    return NoteSummary.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Reply to Thread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_merge_request_discussion_note(
    project_id: str,
    mr_iid: int,
    discussion_id: str,
    body: str,
) -> NoteSummary:
    """Reply to a discussion thread on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        discussion_id: Discussion ID to reply to
        body: Reply text (markdown supported)
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    discussion = mr.discussions.get(discussion_id, lazy=True)
    note = discussion.notes.create({"body": body})
    return NoteSummary.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Edit Thread Reply",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_merge_request_discussion_note(
    project_id: str,
    mr_iid: int,
    discussion_id: str,
    note_id: int,
    body: str,
) -> NoteSummary:
    """Edit a reply in a discussion thread on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        discussion_id: Discussion ID
        note_id: Note ID to edit
        body: Updated reply text (markdown supported)
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    discussion = mr.discussions.get(discussion_id, lazy=True)
    note = discussion.notes.get(note_id, lazy=True)

    note.body = body
    note.save()
    return NoteSummary.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Delete Thread Reply",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_merge_request_discussion_note(
    project_id: str,
    mr_iid: int,
    discussion_id: str,
    note_id: int,
) -> DiscussionNoteDeleteResult:
    """Delete a reply in a discussion thread on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        discussion_id: Discussion ID
        note_id: Note ID to delete
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    discussion = mr.discussions.get(discussion_id, lazy=True)

    logger.warning(
        f"Deleting discussion note {note_id} from discussion {discussion_id} "
        f"in merge request !{mr_iid} in project {project_id}"
    )
    discussion.notes.delete(note_id)

    return DiscussionNoteDeleteResult.model_validate({
        "deleted": True,
        "note_id": note_id,
        "discussion_id": discussion_id,
        "merge_request_iid": mr_iid,
    })


@mcp.tool(
    annotations={
        "title": "Create Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_note(
    project_id: str,
    mr_iid: int,
    body: str,
    position: dict | None = None,
) -> DiscussionSummary:
    """Create a note on a merge request (thread or positioned comment).

    Alias for create_merge_request_thread. Creates a discussion thread
    that can be replied to and resolved.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        body: Comment text (markdown supported)
        position: Optional position dict with keys:
            - base_sha: base commit SHA
            - start_sha: start commit SHA (for multi-commit comments)
            - head_sha: head commit SHA
            - old_path: file path in base version
            - new_path: file path in head version
            - old_line: line number in base version
            - new_line: line number in head version
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)

    data: dict[str, Any] = {"body": body}
    if position:
        data["position"] = position

    discussion = mr.discussions.create(data)
    return DiscussionSummary.from_gitlab(discussion)
