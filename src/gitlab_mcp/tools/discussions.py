"""Discussion and note tools for merge requests and issues."""

import logging
from typing import Any, cast

from gitlab.v4.objects import (
    ProjectMergeRequest,
    ProjectIssue,
    ProjectMergeRequestDiscussion,
    ProjectMergeRequestNote,
    ProjectIssueNote,
    ProjectMergeRequestDiscussionNote,
)
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import DiscussionSummary, NoteSummary
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.serialization import serialize_pydantic

logger = logging.getLogger(__name__)


@mcp.tool(annotations={"title": "MR Discussions", "readOnlyHint": True, "openWorldHint": True})
@serialize_pydantic
def mr_discussions(
    project_id: str,
    mr_iid: int,
    per_page: int = 20,
) -> list[DiscussionSummary]:
    """List discussions/threads on a merge request.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        mr_iid: Merge request number
        per_page: Items per page (default 20, max 100)
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    discussions = paginate(mr.discussions, per_page=per_page)
    return [DiscussionSummary.model_validate(d, from_attributes=True) for d in discussions]


@mcp.tool(annotations={"title": "Issue Discussions", "readOnlyHint": True, "openWorldHint": True})
@serialize_pydantic
def list_issue_discussions(
    project_id: str,
    issue_iid: int,
    per_page: int = 20,
) -> list[DiscussionSummary]:
    """List discussions/threads on an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        per_page: Items per page (default 20, max 100)
    """
    project = get_project(project_id)
    issue = cast(ProjectIssue, project.issues.get(issue_iid))
    discussions = paginate(issue.discussions, per_page=per_page)
    return [DiscussionSummary.model_validate(d, from_attributes=True) for d in discussions]


@mcp.tool(
    annotations={
        "title": "Start Thread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))

    data: dict[str, Any] = {"body": body}
    if position:
        data["position"] = position

    discussion = mr.discussions.create(data)
    return DiscussionSummary.model_validate(discussion, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Resolve Thread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    discussion = cast(ProjectMergeRequestDiscussion, mr.discussions.get(discussion_id))

    discussion.resolved = resolved
    discussion.save()

    # Refresh to get updated details
    discussion = cast(ProjectMergeRequestDiscussion, mr.discussions.get(discussion_id))
    return DiscussionSummary.model_validate(discussion, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Add Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    note = mr.notes.create({"body": body})
    return NoteSummary.model_validate(note, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Edit Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    note = cast(ProjectMergeRequestNote, mr.notes.get(note_id, lazy=True))

    note.body = body
    note.save()
    return NoteSummary.model_validate(note, from_attributes=True)


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
) -> dict:
    """Delete a comment/note from a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        note_id: Note ID to delete
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))

    logger.warning(f"Deleting note {note_id} from merge request !{mr_iid} in project {project_id}")
    mr.notes.delete(note_id)

    return_data: dict[str, Any] = {
        "deleted": True,
        "note_id": note_id,
        "merge_request_iid": mr_iid,
    }
    return return_data


@mcp.tool(
    annotations={
        "title": "Add Issue Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    issue = cast(ProjectIssue, project.issues.get(issue_iid))
    note = issue.notes.create({"body": body})
    return NoteSummary.model_validate(note, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Edit Issue Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    issue = cast(ProjectIssue, project.issues.get(issue_iid))
    note = cast(ProjectIssueNote, issue.notes.get(note_id, lazy=True))

    note.body = body
    note.save()
    return NoteSummary.model_validate(note, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Reply to Thread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    discussion = cast(ProjectMergeRequestDiscussion, mr.discussions.get(discussion_id, lazy=True))
    note = discussion.notes.create({"body": body})
    return NoteSummary.model_validate(note, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Edit Thread Reply",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    discussion = cast(ProjectMergeRequestDiscussion, mr.discussions.get(discussion_id, lazy=True))
    note = cast(ProjectMergeRequestDiscussionNote, discussion.notes.get(note_id, lazy=True))

    note.body = body
    note.save()
    return NoteSummary.model_validate(note, from_attributes=True)


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
) -> dict:
    """Delete a reply in a discussion thread on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: Merge request number
        discussion_id: Discussion ID
        note_id: Note ID to delete
    """
    project = get_project(project_id)
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))
    discussion = cast(ProjectMergeRequestDiscussion, mr.discussions.get(discussion_id, lazy=True))

    logger.warning(
        f"Deleting discussion note {note_id} from discussion {discussion_id} "
        f"in merge request !{mr_iid} in project {project_id}"
    )
    discussion.notes.delete(note_id)

    return_data: dict[str, Any] = {
        "deleted": True,
        "note_id": note_id,
        "discussion_id": discussion_id,
        "merge_request_iid": mr_iid,
    }
    return return_data


@mcp.tool(
    annotations={
        "title": "Create Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
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
    mr = cast(ProjectMergeRequest, project.mergerequests.get(mr_iid))

    data: dict[str, Any] = {"body": body}
    if position:
        data["position"] = position

    discussion = mr.discussions.create(data)
    return DiscussionSummary.model_validate(discussion, from_attributes=True)
