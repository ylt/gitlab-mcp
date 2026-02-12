"""Project tools."""

from typing import Any, cast
from gitlab.v4.objects import Group, Project
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project as _get_project, get_client
from gitlab_mcp.models.projects import ProjectSummary, ProjectMember
from gitlab_mcp.models.base import relative_time
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters, build_sort
from gitlab_mcp.utils.serialization import serialize_pydantic


@mcp.tool(
    annotations={
        "title": "Get Project",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def get_project(project_id: str) -> ProjectSummary:
    """Get project details.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject" or numeric ID)

    Returns:
        Project details including name, description, visibility, branches, etc.
    """
    project = _get_project(project_id)
    return ProjectSummary.model_validate(project, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "List Projects",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def list_projects(
    search: str = "",
    per_page: int = 20,
    visibility: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
    owned: bool = False,
    membership: bool = False,
) -> list[ProjectSummary]:
    """List and search projects.

    Args:
        search: Search query to filter projects by name/description
        per_page: Items per page (default 20, max 100)
        visibility: Filter by visibility (public, internal, private)
        order_by: Sort by field (id, name, path, created_at, updated_at, last_activity_at)
        sort: Sort direction (asc, desc) - default desc
        owned: Return only projects owned by authenticated user (default False)
        membership: Return only projects user is a member of (default False)

    Returns:
        List of project summaries
    """
    client = get_client()

    filters = build_filters(search=search, visibility=visibility)
    filters.update(build_sort(order_by=order_by, sort=sort))

    if owned:
        filters["owned"] = True
    if membership:
        filters["membership"] = True

    projects = paginate(client.projects, per_page=per_page, **filters)
    return [ProjectSummary.model_validate(p, from_attributes=True) for p in projects]


@mcp.tool(
    annotations={
        "title": "List Project Members",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def list_project_members(
    project_id: str,
    search: str = "",
    per_page: int = 20,
    access_level: int | None = None,
    include_inherited: bool = False,
) -> list[ProjectMember]:
    """List members of a project.

    Args:
        project_id: Project ID or path
        search: Search query to filter members by username/name
        per_page: Items per page (default 20, max 100)
        access_level: Filter by access level (10=Guest, 20=Reporter, 30=Developer, 40=Maintainer, 50=Owner)
        include_inherited: Include inherited members from parent groups (default False)

    Returns:
        List of project members with access levels
    """
    project = _get_project(project_id)

    filters = {}
    if search:
        filters["search"] = search
    if access_level is not None:
        filters["access_level"] = access_level
    if include_inherited:
        filters["get_all"] = True

    members = paginate(
        project.members_all if include_inherited else project.members,
        per_page=per_page,
        **filters,
    )
    return [ProjectMember.model_validate(m, from_attributes=True) for m in members]


@mcp.tool(
    annotations={
        "title": "List Group Projects",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def list_group_projects(
    group_id: str,
    per_page: int = 20,
    visibility: str | None = None,
    include_subgroups: bool = False,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[ProjectSummary]:
    """List projects in a group.

    Args:
        group_id: Group ID or path
        per_page: Items per page (default 20, max 100)
        visibility: Filter by visibility (public, internal, private)
        include_subgroups: Include projects from subgroups (default False)
        order_by: Sort by field (id, name, path, created_at, updated_at)
        sort: Sort direction (asc, desc) - default desc

    Returns:
        List of projects in the group
    """
    client = get_client()
    group = cast(Group, client.groups.get(group_id))

    filters = build_filters(visibility=visibility)
    filters.update(build_sort(order_by=order_by, sort=sort))
    if include_subgroups:
        filters["include_subgroups"] = True

    projects = paginate(group.projects, per_page=per_page, **filters)
    return [ProjectSummary.model_validate(p, from_attributes=True) for p in projects]


@mcp.tool(
    annotations={
        "title": "Get Project Activity",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_project_events(
    project_id: str,
    limit: int = 20,
    action: str | None = None,
    target_type: str | None = None,
    user_id: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> list[dict]:
    """Get recent activity/events in a project.

    Args:
        project_id: Project ID or path
        limit: Maximum number of events (default 20)
        action: Filter by action (pushed, commented, merged, etc.)
        target_type: Filter by target type (Issue, MergeRequest, Note, etc.)
        user_id: Filter events by user ID or username (optional)
        after: Filter events after this date (YYYY-MM-DD format)
        before: Filter events before this date (YYYY-MM-DD format)

    Returns:
        List of recent project events with AI-friendly summaries
    """
    project = _get_project(project_id)

    filters = {}
    if action:
        filters["action"] = action
    if target_type:
        filters["target_type"] = target_type
    if user_id:
        filters["author_id"] = user_id
    if after:
        filters["after"] = after
    if before:
        filters["before"] = before

    events = project.events.list(per_page=limit, **filters)

    result = []
    for event in events:
        # Build AI-friendly event summary
        author_name = "unknown"
        author_username = "unknown"
        if hasattr(event, "author") and event.author:
            author_name = event.author.get("name", "unknown")
            author_username = event.author.get("username", "unknown")

        # Extract target details for AI consumption
        target_title = None
        target_url = None
        if hasattr(event, "target_title") and event.target_title:
            target_title = event.target_title
        if hasattr(event, "resource_type") and hasattr(event, "target_id"):
            target_id = event.target_id
            if event.resource_type == "Issue":
                target_url = f"/issues/{target_id}"
            elif event.resource_type == "MergeRequest":
                target_url = f"/merge_requests/{target_id}"

        # Generate human-readable summary
        summary = f"{author_name} {event.action_name}"
        if target_title:
            summary += f": {target_title}"

        result.append(
            {
                "id": event.id,
                "summary": summary,
                "action": event.action_name,
                "target_type": event.target_type,
                "target_title": target_title,
                "target_url": target_url,
                "created_at": relative_time(event.created_at),
                "author": {
                    "username": author_username,
                    "name": author_name,
                },
            }
        )
    return result


@mcp.tool(
    annotations={
        "title": "Fork Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def fork_repository(
    project_id: str,
    namespace: str,
    visibility: str | None = None,
    description: str | None = None,
    issues_enabled: bool | None = None,
    wiki_enabled: bool | None = None,
    snippets_enabled: bool | None = None,
    wait_for_completion: bool = False,
    timeout_seconds: int = 300,
) -> ProjectSummary | dict:
    """Fork a project to a namespace.

    Args:
        project_id: Project ID or path to fork
        namespace: Target namespace/group path for the fork
        visibility: Override fork visibility (public, internal, private)
        description: Override fork description
        issues_enabled: Enable/disable issues in fork (default: inherit from source)
        wiki_enabled: Enable/disable wiki in fork (default: inherit from source)
        snippets_enabled: Enable/disable snippets in fork (default: inherit from source)
        wait_for_completion: Poll and wait for fork to be ready (default False)
        timeout_seconds: Maximum time to wait for fork completion (default 300s)

    Returns:
        Details of the forked project
    """
    import time

    project = _get_project(project_id)
    fork_data = {"namespace": namespace}
    if visibility:
        fork_data["visibility"] = visibility
    if description:
        fork_data["description"] = description
    if issues_enabled is not None:
        fork_data["issues_enabled"] = str(issues_enabled).lower()
    if wiki_enabled is not None:
        fork_data["wiki_enabled"] = str(wiki_enabled).lower()
    if snippets_enabled is not None:
        fork_data["snippets_enabled"] = str(snippets_enabled).lower()

    fork = project.forks.create(fork_data)
    fork_id = fork.id

    # Poll for fork completion if requested
    if wait_for_completion:
        client = get_client()
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            fork = cast(Project, client.projects.get(fork_id))
            # Fork is ready when import_source is None/empty
            if not hasattr(fork, "import_source") or not fork.import_source:
                break
            time.sleep(2)
        else:
            # Timeout occurred - return dict with warning
            return {
                **ProjectSummary.model_validate(fork, from_attributes=True).model_dump(),
                "warning": f"Fork did not complete within {timeout_seconds}s, returning current state",
            }

    return ProjectSummary.model_validate(fork, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Create Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
@serialize_pydantic
def create_repository(
    name: str,
    namespace: str,
    description: str = "",
    visibility: str = "private",
    initialize_with_readme: bool = False,
    default_branch: str = "main",
    license_template: str | None = None,
    gitignore_template: str | None = None,
    issue_template_key: str | None = None,
    merge_request_template_key: str | None = None,
    cicd_template_key: str | None = None,
    wiki_enabled: bool = True,
    issues_enabled: bool = True,
    snippets_enabled: bool = True,
    container_registry_enabled: bool = True,
) -> ProjectSummary:
    """Create a new project/repository.

    Args:
        name: Project name
        namespace: Namespace/group path or user path (e.g., "myusername" or "mygroup")
        description: Project description
        visibility: Project visibility (private, internal, public)
        initialize_with_readme: Create initial README.md file (default False)
        default_branch: Default branch name (default "main")
        license_template: License template to use (e.g., "mit", "apache-2.0")
        gitignore_template: Gitignore template to use (e.g., "Python", "Node")
        issue_template_key: Issue template key to use (e.g., "bug", "feature")
        merge_request_template_key: Merge request template key to use
        cicd_template_key: CI/CD template key to use (e.g., "docker", "nodejs")
        wiki_enabled: Enable wiki (default True)
        issues_enabled: Enable issues (default True)
        snippets_enabled: Enable snippets (default True)
        container_registry_enabled: Enable container registry (default True)

    Returns:
        Details of the created project
    """
    client = get_client()
    project_data = {
        "name": name,
        "namespace_id": namespace,
        "description": description,
        "visibility": visibility,
        "initialize_with_readme": initialize_with_readme,
        "default_branch": default_branch,
        "wiki_enabled": wiki_enabled,
        "issues_enabled": issues_enabled,
        "snippets_enabled": snippets_enabled,
        "container_registry_enabled": container_registry_enabled,
    }
    if license_template:
        project_data["license_template"] = license_template
    if gitignore_template:
        project_data["gitignore_template"] = gitignore_template
    if issue_template_key:
        project_data["issue_template_key"] = issue_template_key
    if merge_request_template_key:
        project_data["merge_request_template_key"] = merge_request_template_key
    if cicd_template_key:
        project_data["cicd_template_key"] = cicd_template_key

    project = client.projects.create(project_data)
    return ProjectSummary.model_validate(project, from_attributes=True)
