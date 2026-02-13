"""Issue tools."""

from typing import Any
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project, get_client
from gitlab_mcp.models import (
    IssueSummary,
    IssueNote,
    IssueLink,
    IssueDeleteResult,
    IssueLinkDeleteResult,
    RelatedMergeRequest,
    IssueTimeStats,
    IssueTimeAddResult,
)
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters, build_sort


def lookup_user_id(username: str) -> int | None:
    """Look up user ID from username.

    Args:
        username: GitLab username to look up

    Returns:
        User ID if found, None otherwise
    """
    try:
        client = get_client()
        users = client.users.list(username=username)
        if users and len(users) > 0:
            return users[0].id
        return None
    except Exception:
        return None


@mcp.tool(annotations={"title": "Get Issue", "readOnlyHint": True, "openWorldHint": True})
def get_issue(project_id: str, issue_iid: int) -> IssueSummary:
    """Get details of an issue.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        issue_iid: Issue number within the project
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    return IssueSummary.from_gitlab(issue)


@mcp.tool(annotations={"title": "List Issues", "readOnlyHint": True, "openWorldHint": True})
def list_issues(
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
) -> list[IssueSummary]:
    """List issues in a project.

    Args:
        project_id: Project ID or path
        per_page: Items per page (default 20, max 100)
        state: Filter by state: opened, closed, all
        author_username: Filter by author username
        assignee_username: Filter by assignee username
        labels: Comma-separated list of labels to filter by
        milestone: Filter by milestone title
        search: Search in title and description
        created_after: Filter by creation date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
        created_before: Filter by creation date (ISO format)
        order_by: Sort by field: created_at, updated_at, priority, label_priority
        sort: Sort direction: asc or desc (default: desc)
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

    # Add sorting
    filters.update(build_sort(order_by=order_by, sort=sort))

    # Fetch paginated results
    issues = paginate(
        project.issues,
        per_page=per_page,
        **filters,
    )

    return IssueSummary.from_gitlab(issues)


@mcp.tool(
    annotations={
        "title": "Create Issue",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_issue(
    project_id: str,
    title: str,
    description: str = "",
    labels: str = "",
    assignee_username: str = "",
    confidential: bool = False,
    weight: int | None = None,
    due_date: str | None = None,
) -> IssueSummary:
    """Create a new issue.

    Args:
        project_id: Project ID or path
        title: Issue title
        description: Issue description (markdown supported)
        labels: Comma-separated list of labels
        assignee_username: Username to assign the issue to
        confidential: Mark issue as confidential
        weight: Issue weight (for issue boards)
        due_date: Due date in YYYY-MM-DD format
    """
    project = get_project(project_id)
    data: dict[str, Any] = {"title": title, "description": description}
    if labels:
        data["labels"] = labels
    if assignee_username:
        user_id = lookup_user_id(assignee_username)
        if user_id:
            data["assignee_ids"] = [user_id]
    if confidential:
        data["confidential"] = confidential
    if weight is not None:
        data["weight"] = weight
    if due_date is not None:
        data["due_date"] = due_date
    issue = project.issues.create(data)
    return IssueSummary.from_gitlab(issue)


@mcp.tool(
    annotations={
        "title": "Update Issue",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_issue(
    project_id: str,
    issue_iid: int,
    title: str = "",
    description: str = "",
    state_event: str = "",
    labels: str = "",
    confidential: bool | None = None,
    weight: int | None = None,
    due_date: str | None = None,
) -> IssueSummary:
    """Update an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        title: New title (leave empty to keep current)
        description: New description (leave empty to keep current)
        state_event: "close" or "reopen" to change state
        labels: New comma-separated labels (replaces existing)
        confidential: Mark issue as confidential
        weight: Issue weight (for issue boards)
        due_date: Due date in YYYY-MM-DD format
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    if title:
        issue.title = title
    if description:
        issue.description = description
    if state_event:
        issue.state_event = state_event
    if labels:
        issue.labels = labels.split(",")
    if confidential is not None:
        issue.confidential = confidential
    if weight is not None:
        issue.weight = weight
    if due_date is not None:
        issue.due_date = due_date
    issue.save()
    return IssueSummary.from_gitlab(issue)


@mcp.tool(
    annotations={
        "title": "Add Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def add_issue_comment(
    project_id: str,
    issue_iid: int,
    body: str,
) -> IssueNote:
    """Add a comment to an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        body: Comment text (markdown supported)
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    note = issue.notes.create({"body": body})
    return IssueNote.from_gitlab(note)


@mcp.tool(
    annotations={
        "title": "Delete Issue",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_issue(project_id: str, issue_iid: int) -> IssueDeleteResult:
    """Delete an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    issue.delete()
    return IssueDeleteResult.model_validate({"status": "deleted", "issue_iid": issue_iid})


@mcp.tool(annotations={"title": "My Issues", "readOnlyHint": True, "openWorldHint": True})
def my_issues(state: str = "opened", scope: str = "all", limit: int = 20) -> list[IssueSummary]:
    """List current user's issues.

    Args:
        state: Filter by state: opened, closed, all
        scope: Filter by scope: created_by_me, assigned_to_me, all
        limit: Maximum number of results
    """
    client = get_client()
    kwargs: dict[str, Any] = {"state": state, "scope": scope, "per_page": limit}
    issues_list: Any = client.issues.list(**kwargs)
    return IssueSummary.from_gitlab(issues_list)


@mcp.tool(annotations={"title": "List Issue Links", "readOnlyHint": True, "openWorldHint": True})
def list_issue_links(project_id: str, issue_iid: int) -> list[IssueLink]:
    """List linked issues.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    links = issue.links.list()
    return IssueLink.from_gitlab(links)


@mcp.tool(annotations={"title": "Get Issue Link", "readOnlyHint": True, "openWorldHint": True})
def get_issue_link(project_id: str, issue_iid: int, link_id: int) -> IssueLink:
    """Get details of a linked issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        link_id: Link ID
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    links = issue.links.list()
    link = next((lnk for lnk in links if lnk.id == link_id), None)
    if not link:
        raise ValueError(f"Link {link_id} not found")
    return IssueLink.from_gitlab(link)


@mcp.tool(
    annotations={
        "title": "Link Issues",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_issue_link(
    project_id: str,
    issue_iid: int,
    target_project_id: str,
    target_issue_iid: int,
    link_type: str = "relates_to",
) -> IssueLink:
    """Create a link between two issues.

    Args:
        project_id: Source project ID or path
        issue_iid: Source issue number
        target_project_id: Target project ID or path
        target_issue_iid: Target issue number
        link_type: Type of link: relates_to, blocks, is_blocked_by
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    target_project = get_project(target_project_id)
    data: dict[str, Any] = {
        "target_project_id": target_project.id,
        "target_issue_iid": target_issue_iid,
        "link_type": link_type,
    }
    result = issue.links.create(data)
    link = result[0] if isinstance(result, tuple) else result
    return IssueLink.from_gitlab(link)


@mcp.tool(
    annotations={
        "title": "Unlink Issues",
        "readOnlyHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_issue_link(project_id: str, issue_iid: int, link_id: int) -> IssueLinkDeleteResult:
    """Delete an issue link.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        link_id: Link ID to delete
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    links = issue.links.list()
    link = next((lnk for lnk in links if lnk.id == link_id), None)
    if not link:
        raise ValueError(f"Link {link_id} not found")
    link.delete()
    return IssueLinkDeleteResult.model_validate({"status": "deleted", "link_id": link_id})


@mcp.tool(annotations={"title": "Related MRs", "readOnlyHint": True, "openWorldHint": True})
def list_related_merge_requests(project_id: str, issue_iid: int) -> list[RelatedMergeRequest]:
    """List merge requests that will close this issue when merged.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    mrs = issue.related_merge_requests()
    return RelatedMergeRequest.from_gitlab(mrs)


@mcp.tool(
    annotations={
        "title": "Log Time",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def add_time_spent(project_id: str, issue_iid: int, duration: str) -> IssueTimeAddResult:
    """Add time spent on an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
        duration: Duration format - examples: 1h, 30m, 1h30m, 2d, 1w3d2h
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    issue.add_spent_time(duration)
    return IssueTimeAddResult.model_validate({
        "status": "time_added",
        "duration": duration,
        "issue_iid": issue_iid,
        "total_time_spent": issue.time_stats().get("total_time_spent", 0),
    })


@mcp.tool(annotations={"title": "Time Stats", "readOnlyHint": True, "openWorldHint": True})
def get_time_stats(project_id: str, issue_iid: int) -> IssueTimeStats:
    """Get time tracking statistics for an issue.

    Args:
        project_id: Project ID or path
        issue_iid: Issue number
    """
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)
    stats = issue.time_stats()
    return IssueTimeStats.from_gitlab(stats)  # type: ignore[arg-type]
