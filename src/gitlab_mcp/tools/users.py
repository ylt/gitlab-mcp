"""User tools."""

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_client
from gitlab_mcp.models import UserSummary, EventSummary
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters, build_sort


@mcp.tool(
    annotations={
        "title": "Search Users",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_users(
    search: str = "",
    per_page: int = 20,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[UserSummary]:
    """Search users by username or name.

    Args:
        search: Search query (username or name substring)
        per_page: Items per page (max 100)
        order_by: Sort by field (id, name, username, created_at, updated_at)
        sort: Sort direction (asc, desc)
    """
    client = get_client()
    filters = {
        **build_filters(search=search if search else None),
        **build_sort(order_by=order_by, sort=sort),
    }
    users = paginate(
        client.users,
        per_page=per_page,
        **filters,
    )
    return UserSummary.from_gitlab(users)


@mcp.tool(
    annotations={
        "title": "List User Events",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_events(limit: int = 20) -> list[EventSummary]:
    """List authenticated user's events and activity.

    Args:
        limit: Maximum number of events to return
    """
    client = get_client()
    events = client.events.list(per_page=limit)
    return EventSummary.from_gitlab(events)
