"""Merge request tools."""

from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from typing import Any

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import (
    MergeRequestSummary,
    MergeRequestDiff,
    ApprovalResult,
    ApprovalStateDetailed,
    MergeRequestNote,
    MergeRequestVersion,
    FileChange,
    ChangesSummary,
)
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters, build_sort


@mcp.tool(
    annotations={
        "title": "Get Merge Request",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_merge_request(project_id: str, merge_request_iid: int) -> MergeRequestSummary:
    """Get details of a merge request.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        merge_request_iid: MR number within the project
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(merge_request_iid)
    return MergeRequestSummary.from_gitlab(mr)


@mcp.tool(
    annotations={
        "title": "List Merge Requests",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_merge_requests(
    project_id: str,
    per_page: int = 20,
    state: str | None = None,
    author_username: str | None = None,
    assignee_username: str | None = None,
    labels: str | None = None,
    milestone: str | None = None,
    search: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[MergeRequestSummary]:
    """List merge requests in a project with filtering and sorting.

    Args:
        project_id: Project ID or path
        per_page: Items per page (default 20, max 100)
        state: Filter by state: opened, closed, merged, locked, all
        author_username: Filter by author username
        assignee_username: Filter by assignee username
        labels: Comma-separated label names (e.g., "bug,urgent")
        milestone: Filter by milestone title
        search: Search in title and description
        created_after: Filter by creation date (ISO 8601 format)
        created_before: Filter by creation date (ISO 8601 format)
        order_by: Sort by field: created_at, updated_at, title
        sort: Sort direction: asc or desc (default desc)
    """
    project = get_project(project_id)

    # Build filters
    filters = build_filters(
        state=state,
        author_username=author_username,
        assignee_username=assignee_username,
        labels=labels.split(",") if labels else None,
        milestone=milestone,
        search=search,
        created_after=created_after,
        created_before=created_before,
    )

    # Build sort parameters
    sort_params = build_sort(order_by=order_by, sort=sort)

    # Combine filters and sort parameters
    all_params: dict[str, Any] = {**filters, **sort_params}

    # Paginate results
    mrs = paginate(
        project.mergerequests,
        per_page=per_page,
        **all_params,
    )

    return [MergeRequestSummary.from_gitlab(mr) for mr in mrs]


@mcp.tool(
    annotations={
        "title": "Create Merge Request",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_merge_request(
    project_id: str,
    source_branch: str,
    target_branch: str,
    title: str,
    description: str = "",
    draft: bool = False,
    assignee_ids: list[int] | None = None,
    reviewer_ids: list[int] | None = None,
    labels: list[str] | None = None,
    milestone_id: int | None = None,
) -> MergeRequestSummary:
    """Create a new merge request.

    Args:
        project_id: Project ID or path
        source_branch: Branch containing the changes
        target_branch: Branch to merge into (usually main/master)
        title: MR title
        description: MR description (markdown supported)
        draft: Create as draft MR (default False)
        assignee_ids: List of assignee user IDs
        reviewer_ids: List of reviewer user IDs
        labels: List of label names to apply
        milestone_id: Milestone ID to assign
    """
    project = get_project(project_id)
    data: dict[str, Any] = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "description": description,
        "draft": draft,
    }
    if assignee_ids is not None:
        data["assignee_ids"] = assignee_ids
    if reviewer_ids is not None:
        data["reviewer_ids"] = reviewer_ids
    if labels is not None:
        data["labels"] = labels
    if milestone_id is not None:
        data["milestone_id"] = milestone_id

    mr = project.mergerequests.create(data)
    return MergeRequestSummary.from_gitlab(mr)


@mcp.tool(
    annotations={
        "title": "Merge MR",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def merge_merge_request(
    project_id: str,
    merge_request_iid: int,
    squash: bool = False,
    delete_source_branch: bool = False,
    merge_commit_message: str | None = None,
    squash_commit_message: str | None = None,
    should_remove_source_branch: bool = False,
) -> MergeRequestSummary:
    """Merge a merge request.

    Args:
        project_id: Project ID or path
        merge_request_iid: MR number
        squash: Squash commits into one
        delete_source_branch: Delete source branch after merge (deprecated, use should_remove_source_branch)
        merge_commit_message: Custom merge commit message
        squash_commit_message: Custom squash commit message
        should_remove_source_branch: Delete source branch after merge
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(merge_request_iid)

    # Use should_remove_source_branch if provided, otherwise fall back to delete_source_branch for backwards compatibility
    remove_source = should_remove_source_branch or delete_source_branch

    merge_kwargs: dict[str, bool | str] = {
        "squash": squash,
        "should_remove_source_branch": remove_source,
    }
    if merge_commit_message is not None:
        merge_kwargs["merge_commit_message"] = merge_commit_message
    if squash_commit_message is not None:
        merge_kwargs["squash_commit_message"] = squash_commit_message

    mr.merge(**merge_kwargs)  # type: ignore[arg-type]
    # Refresh to get updated state
    mr = project.mergerequests.get(merge_request_iid)
    return MergeRequestSummary.from_gitlab(mr)


@mcp.tool(
    annotations={
        "title": "Get MR Diff",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_merge_request_diff(
    project_id: str,
    merge_request_iid: int,
    file_pattern: str | None = None,
    max_diff_lines: int = 500,
    summary_only: bool = False,
) -> list[MergeRequestDiff]:
    """Get the file changes in a merge request.

    Args:
        project_id: Project ID or path
        merge_request_iid: MR number
        file_pattern: Filter diffs by file path pattern (glob-style, e.g., "*.py" or "src/**/*.ts")
        max_diff_lines: Truncate large diffs with "[truncated]" message (default 500)
        summary_only: Return only file list without diffs (default False)
    """
    from fnmatch import fnmatch

    project = get_project(project_id)
    mr = project.mergerequests.get(merge_request_iid)
    changes = mr.changes()

    # Transform to AI-friendly format
    diffs = []
    changes_list = changes.get("changes", []) if isinstance(changes, dict) else []
    for change in changes_list:
        path = change["new_path"]

        # Apply file pattern filter if provided
        if file_pattern and not fnmatch(path, file_pattern):
            continue

        # Modify the diff field for truncation/summary as needed
        if summary_only:
            change = {**change, "diff": ""}
        elif max_diff_lines > 0:
            diff_text = change.get("diff") or ""
            if diff_text:
                lines = diff_text.split("\n")
                if len(lines) > max_diff_lines:
                    diff_text = (
                        "\n".join(lines[:max_diff_lines])
                        + f"\n[truncated: {len(lines) - max_diff_lines} more lines]"
                    )
                    change = {**change, "diff": diff_text}

        # Pass the change dict directly to model_validate
        diffs.append(MergeRequestDiff.model_validate(change))
    return diffs


def _diff_status(change: dict) -> str:
    """Get human-readable diff status."""
    if change.get("new_file"):
        return "added"
    if change.get("deleted_file"):
        return "deleted"
    if change.get("renamed_file"):
        return "renamed"
    return "modified"


@mcp.tool(
    annotations={
        "title": "Summarize Changes",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def summarize_merge_request_changes(
    project_id: str,
    mr_iid: int,
) -> ChangesSummary:
    """Get a high-level summary of MR changes.

    Args:
        project_id: Project ID or path
        mr_iid: MR number

    Returns:
        Summary containing files changed, additions, deletions, and per-file details
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    changes = mr.changes()

    files = []
    total_additions = 0
    total_deletions = 0

    changes_list = changes.get("changes", []) if isinstance(changes, dict) else []
    for change in changes_list:
        # Parse diff to count additions/deletions
        diff_text = change.get("diff", "")
        additions = 0
        deletions = 0

        for line in diff_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        total_additions += additions
        total_deletions += deletions

        # Add status and stats to change dict
        change["status"] = _diff_status(change)
        change["additions"] = additions
        change["deletions"] = deletions
        files.append(FileChange.from_gitlab(change))

    return ChangesSummary.model_validate({
        "files_changed": len(files),
        "additions": total_additions,
        "deletions": total_deletions,
        "files": files,
    })


@mcp.tool(
    annotations={
        "title": "Approve MR",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def approve_merge_request(project_id: str, merge_request_iid: int) -> ApprovalResult:
    """Approve a merge request.

    Args:
        project_id: Project ID or path
        merge_request_iid: MR number
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(merge_request_iid)
    mr.approve()
    return ApprovalResult.model_validate({"approved": True, "merge_request_iid": merge_request_iid})


@mcp.tool(
    annotations={
        "title": "Unapprove MR",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def unapprove_merge_request(project_id: str, merge_request_iid: int) -> ApprovalResult:
    """Remove your approval from a merge request.

    Args:
        project_id: Project ID or path
        merge_request_iid: MR number
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(merge_request_iid)
    mr.unapprove()
    return ApprovalResult.model_validate({"approved": False, "merge_request_iid": merge_request_iid})


@mcp.tool(
    annotations={
        "title": "Update MR",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_merge_request(
    project_id: str,
    mr_iid: int,
    title: str | None = None,
    description: str | None = None,
    target_branch: str | None = None,
    labels: list[str] | None = None,
    assignee_ids: list[int] | None = None,
) -> MergeRequestSummary:
    """Update a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: MR number
        title: New MR title
        description: New MR description
        target_branch: New target branch
        labels: List of label names to assign
        assignee_ids: List of assignee user IDs
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)

    # Update attributes directly on the MR object
    if title is not None:
        mr.title = title
    if description is not None:
        mr.description = description
    if target_branch is not None:
        mr.target_branch = target_branch
    if labels is not None:
        mr.labels = labels
    if assignee_ids is not None:
        mr.assignee_ids = assignee_ids

    mr.save()
    # Refresh to get updated state
    mr = project.mergerequests.get(mr_iid)
    return MergeRequestSummary.from_gitlab(mr)


@mcp.tool(
    annotations={
        "title": "Approval Status",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_merge_request_approval_state(project_id: str, mr_iid: int) -> ApprovalStateDetailed:
    """Get approval state of a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: MR number
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    approvals = mr.approvals.get()
    return ApprovalStateDetailed.from_gitlab(approvals)


@mcp.tool(
    annotations={
        "title": "List MR Comments",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_merge_request_notes(
    project_id: str,
    mr_iid: int,
    limit: int = 20,
) -> list[MergeRequestNote]:
    """List comments (notes) on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: MR number
        limit: Maximum number of notes to return
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    notes = mr.notes.list(per_page=limit)
    return [MergeRequestNote.from_gitlab(note) for note in notes]


@mcp.tool(
    annotations={
        "title": "Get MR Comment",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_merge_request_note(
    project_id: str,
    mr_iid: int,
    note_id: int,
) -> MergeRequestNote:
    """Get a specific comment (note) on a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: MR number
        note_id: Note ID
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    note = mr.notes.get(note_id)
    return MergeRequestNote.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "List MR Diffs",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_merge_request_diffs(
    project_id: str,
    mr_iid: int,
    limit: int = 20,
) -> list[MergeRequestDiff]:
    """List file diffs in a merge request with pagination.

    Args:
        project_id: Project ID or path
        mr_iid: MR number
        limit: Maximum number of diffs to return
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    diffs = mr.diffs.list(per_page=limit)

    return [MergeRequestDiff.from_gitlab(diff) for diff in diffs]


@mcp.tool(
    annotations={
        "title": "List MR Versions",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_merge_request_versions(project_id: str, mr_iid: int) -> list[MergeRequestVersion]:
    """List versions (iterations) of a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: MR number
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    versions = mr.versions.list()
    return [
        MergeRequestVersion.from_gitlab(version) for version in versions
    ]


@mcp.tool(
    annotations={
        "title": "Get MR Version",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_merge_request_version(
    project_id: str,
    mr_iid: int,
    version_id: int,
) -> MergeRequestVersion:
    """Get a specific version (iteration) of a merge request.

    Args:
        project_id: Project ID or path
        mr_iid: MR number
        version_id: Version ID
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    version = mr.versions.get(version_id)
    return MergeRequestVersion.from_gitlab(version)


@mcp.tool(
    annotations={
        "title": "Get All MR Diffs",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_merge_request_diffs(
    project_id: str,
    mr_iid: int,
) -> list[MergeRequestDiff]:
    """Get all diffs for a merge request (alias for list_merge_request_diffs without pagination).

    Args:
        project_id: Project ID or path
        mr_iid: MR number
    """
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)
    diffs = mr.diffs.list(get_all=True)

    return [MergeRequestDiff.from_gitlab(diff) for diff in diffs]
