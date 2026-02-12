"""Milestone tools."""

from typing import Any, cast
from gitlab.v4.objects import ProjectMilestone, ProjectIssue
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import MilestoneSummary, IssueSummary, MergeRequestSummary
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters, build_sort
from gitlab_mcp.utils.validation import validate_date
from gitlab_mcp.utils.serialization import serialize_pydantic


@mcp.tool(
    annotations={
        "title": "List Milestones",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def list_milestones(
    project_id: str,
    per_page: int = 20,
    state: str | None = None,
    search: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[MilestoneSummary]:
    """List milestones in a project.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        per_page: Items per page (default 20, max 100)
        state: Filter by state: active, closed, all (None means active)
        search: Search milestones by title and description
        order_by: Sort by field (created_at, updated_at, due_date, title)
        sort: Sort direction: asc or desc (default desc)
    """
    project = get_project(project_id)
    filters = build_filters(state=state, search=search)
    sort_params = build_sort(order_by=order_by, sort=sort)
    milestones = paginate(
        project.milestones,
        per_page=per_page,
        **filters,
        **sort_params,
    )
    return [MilestoneSummary.model_validate(m, from_attributes=True) for m in milestones]


@mcp.tool(
    annotations={
        "title": "Get Milestone",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def get_milestone(project_id: str, milestone_id: int) -> MilestoneSummary:
    """Get details of a milestone.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID
    """
    project = get_project(project_id)
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    return MilestoneSummary.model_validate(milestone, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Create Milestone",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
@serialize_pydantic
def create_milestone(
    project_id: str,
    title: str,
    description: str = "",
    due_date: str = "",
    start_date: str = "",
) -> MilestoneSummary:
    """Create a new milestone.

    Args:
        project_id: Project ID or path
        title: Milestone title
        description: Milestone description (markdown supported)
        due_date: Due date in YYYY-MM-DD format
        start_date: Start date in YYYY-MM-DD format
    """
    project = get_project(project_id)
    data = {"title": title}
    if description:
        data["description"] = description
    if due_date:
        data["due_date"] = validate_date(due_date)
    if start_date:
        data["start_date"] = validate_date(start_date)
    milestone = cast(ProjectMilestone, project.milestones.create(data))
    return MilestoneSummary.model_validate(milestone, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Update Milestone",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def edit_milestone(
    project_id: str,
    milestone_id: int,
    title: str = "",
    description: str = "",
    due_date: str = "",
    start_date: str = "",
    state_event: str = "",
) -> MilestoneSummary:
    """Update a milestone.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID
        title: New title (leave empty to keep current)
        description: New description (leave empty to keep current)
        due_date: New due date in YYYY-MM-DD format (leave empty to keep current)
        start_date: New start date in YYYY-MM-DD format (leave empty to keep current)
        state_event: "close" or "activate" to change state
    """
    project = get_project(project_id)
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    if title:
        milestone.title = title
    if description:
        milestone.description = description
    if due_date:
        milestone.due_date = validate_date(due_date)
    if start_date:
        milestone.start_date = validate_date(start_date)
    if state_event:
        milestone.state_event = state_event
    milestone.save()
    return MilestoneSummary.model_validate(milestone, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Delete Milestone",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
def delete_milestone(project_id: str, milestone_id: int) -> dict[str, Any]:
    """Delete a milestone.

    Note: Issues and MRs assigned to this milestone will have their milestone cleared.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID
    """
    project = get_project(project_id)
    project.milestones.delete(milestone_id)
    return {"success": True, "message": f"Milestone {milestone_id} deleted"}


@mcp.tool(
    annotations={
        "title": "List Milestone Issues",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def get_milestone_issues(
    project_id: str,
    milestone_id: int,
    per_page: int = 20,
    state: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[IssueSummary]:
    """List issues in a milestone.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID
        per_page: Items per page (default 20, max 100)
        state: Filter by state: opened, closed, all
        order_by: Sort by field (created_at, updated_at, priority, due_date, title)
        sort: Sort direction: asc or desc (default desc)
    """
    project = get_project(project_id)
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    filters = build_filters(state=state)
    sort_params = build_sort(order_by=order_by, sort=sort)
    issues = paginate(
        milestone.issues,
        per_page=per_page,
        **filters,
        **sort_params,
    )
    return [IssueSummary.model_validate(i, from_attributes=True) for i in issues]


@mcp.tool(
    annotations={
        "title": "List Milestone Merge Requests",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def get_milestone_merge_requests(
    project_id: str,
    milestone_id: int,
    per_page: int = 20,
    state: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[MergeRequestSummary]:
    """List merge requests in a milestone.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID
        per_page: Items per page (default 20, max 100)
        state: Filter by state: opened, closed, locked, merged, all
        order_by: Sort by field (created_at, updated_at, title)
        sort: Sort direction: asc or desc (default desc)
    """
    project = get_project(project_id)
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    filters = build_filters(state=state)
    sort_params = build_sort(order_by=order_by, sort=sort)
    mrs = paginate(
        milestone.merge_requests,
        per_page=per_page,
        **filters,
        **sort_params,
    )
    return [MergeRequestSummary.model_validate(mr, from_attributes=True) for mr in mrs]


@mcp.tool(
    annotations={
        "title": "Get Milestone Burndown Events",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
def get_milestone_burndown_events(
    project_id: str,
    milestone_id: int,
) -> list[dict[str, Any]]:
    """Get burndown chart events for a milestone.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID
    """
    project = get_project(project_id)
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    events = milestone.burndown_events.list(get_all=True)
    return [
        {
            "id": event.id,
            "created_at": event.created_at,
            "weight": event.weight,
            "user_id": event.user_id,
            "issue_id": event.issue_id,
        }
        for event in events
    ]


@mcp.tool(
    annotations={
        "title": "Get Milestone Issue",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def get_milestone_issue(
    project_id: str,
    milestone_id: int,
    issue_iid: int,
) -> IssueSummary:
    """Get a specific issue in a milestone.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID
        issue_iid: Issue number within the project
    """
    project = get_project(project_id)
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    issue_data: Any = milestone.issues.get(issue_iid)  # type: ignore[union-attr]
    issue = cast(ProjectIssue, issue_data)
    return IssueSummary.model_validate(issue, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Promote Milestone",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def promote_milestone(project_id: str, milestone_id: int) -> dict:
    """Promote a project milestone to a group milestone.

    Args:
        project_id: Project ID or path
        milestone_id: Milestone ID to promote
    """
    project = get_project(project_id)
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    milestone.promote()
    # Refresh to get updated state
    milestone = cast(ProjectMilestone, project.milestones.get(milestone_id))
    result = MilestoneSummary.model_validate(milestone, from_attributes=True).model_dump()
    result["promoted"] = True
    return result
