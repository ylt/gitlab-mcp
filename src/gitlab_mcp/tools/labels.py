"""Label tools."""

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import LabelSummary, LabelDeleteResult, LabelSubscriptionResult
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters
from gitlab_mcp.utils.validation import validate_color


@mcp.tool(
    annotations={
        "title": "List Labels",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_labels(
    project_id: str,
    per_page: int = 20,
    search: str | None = None,
) -> list[LabelSummary]:
    """List all labels in a project.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        per_page: Items per page (max 100)
        search: Search labels by name
    """
    project = get_project(project_id)
    filters = build_filters(search=search)
    labels = paginate(
        project.labels,
        per_page=per_page,
        **filters,
    )
    return LabelSummary.from_gitlab(labels)


@mcp.tool(
    annotations={
        "title": "Get Label",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_label(project_id: str, label_id: int) -> LabelSummary:
    """Get details of a specific label.

    Args:
        project_id: Project ID or path
        label_id: Label ID
    """
    project = get_project(project_id)
    label = project.labels.get(label_id)
    return LabelSummary.from_gitlab(label)


@mcp.tool(
    annotations={
        "title": "Create Label",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_label(
    project_id: str,
    name: str,
    color: str,
    description: str = "",
    priority: int | None = None,
) -> LabelSummary:
    """Create a new label in a project.

    Args:
        project_id: Project ID or path
        name: Label name
        color: Label color (hex code, e.g., "#FF0000")
        description: Label description
        priority: Label priority (lower number = higher priority)
    """
    project = get_project(project_id)
    validated_color = validate_color(color)
    data: dict[str, str | int] = {"name": name, "color": f"#{validated_color}"}
    if description:
        data["description"] = description
    if priority is not None:
        data["priority"] = priority
    label = project.labels.create(data)
    return LabelSummary.from_gitlab(label)


@mcp.tool(
    annotations={
        "title": "Update Label",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_label(
    project_id: str,
    label_id: int,
    name: str = "",
    color: str = "",
    description: str = "",
) -> LabelSummary:
    """Update a label.

    Args:
        project_id: Project ID or path
        label_id: Label ID
        name: New label name (leave empty to keep current)
        color: New color (hex code, leave empty to keep current)
        description: New description (leave empty to keep current)
    """
    project = get_project(project_id)
    label = project.labels.get(label_id)
    data = {}
    if name:
        data["name"] = name
    if color:
        validated_color = validate_color(color)
        data["color"] = f"#{validated_color}"
    if description is not None and description != "":
        data["description"] = description
    if data:
        label.update(data)
    return LabelSummary.from_gitlab(label)


@mcp.tool(
    annotations={
        "title": "Delete Label",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_label(project_id: str, label_id: int) -> LabelDeleteResult:
    """Delete a label.

    Note: The label will be removed from all issues and MRs that use it.

    Args:
        project_id: Project ID or path
        label_id: Label ID
    """
    project = get_project(project_id)
    project.labels.delete(label_id)
    return LabelDeleteResult.model_validate({"id": label_id, "deleted": True})


@mcp.tool(
    annotations={
        "title": "Promote Label to Group",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def promote_label_to_group(project_id: str, label_name: str) -> LabelSummary:
    """Promote a project label to a group label.

    The label will be available to all projects in the group.

    Args:
        project_id: Project ID or path
        label_name: Name of the label to promote
    """
    project = get_project(project_id)
    # Get label by name
    labels = project.labels.list(search=label_name, get_all=False)
    label = next((lbl for lbl in labels if lbl.name == label_name), None)
    if not label:
        raise ValueError(f"Label '{label_name}' not found in project")

    # Promote to group
    promoted = label.promote()
    return LabelSummary.from_gitlab(promoted)


@mcp.tool(
    annotations={
        "title": "Subscribe to Label",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def subscribe_to_label(project_id: str, label_name: str) -> LabelSubscriptionResult:
    """Subscribe to notifications for a label.

    Args:
        project_id: Project ID or path
        label_name: Name of the label to subscribe to
    """
    project = get_project(project_id)
    # Get label by name
    labels = project.labels.list(search=label_name, get_all=False)
    label = next((lbl for lbl in labels if lbl.name == label_name), None)
    if not label:
        raise ValueError(f"Label '{label_name}' not found in project")

    # Subscribe
    label.subscribe()
    return LabelSubscriptionResult.model_validate({
        "name": label.name,
        "subscribed": True,
        "message": f"Subscribed to notifications for label '{label.name}'",
    })


@mcp.tool(
    annotations={
        "title": "Unsubscribe from Label",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def unsubscribe_from_label(project_id: str, label_name: str) -> LabelSubscriptionResult:
    """Unsubscribe from notifications for a label.

    Args:
        project_id: Project ID or path
        label_name: Name of the label to unsubscribe from
    """
    project = get_project(project_id)
    # Get label by name
    labels = project.labels.list(search=label_name, get_all=False)
    label = next((lbl for lbl in labels if lbl.name == label_name), None)
    if not label:
        raise ValueError(f"Label '{label_name}' not found in project")

    # Unsubscribe
    label.unsubscribe()
    return LabelSubscriptionResult.model_validate({
        "name": label.name,
        "subscribed": False,
        "message": f"Unsubscribed from notifications for label '{label.name}'",
    })
