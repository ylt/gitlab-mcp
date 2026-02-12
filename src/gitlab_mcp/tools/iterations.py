"""Iteration and sprint tools."""

from typing import Any
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_client
from gitlab_mcp.models import IterationSummary


@mcp.tool(
    annotations={"title": "List Group Iterations", "readOnlyHint": True, "openWorldHint": True}
)
def list_group_iterations(
    group_id: str, state: str = "all", limit: int = 20
) -> list[IterationSummary]:
    """List iterations (sprints) in a group.

    Args:
        group_id: Group ID or path (e.g., "mygroup")
        state: Filter by state: upcoming, current, opened, closed, all
        limit: Maximum number of results
    """
    client = get_client()
    group = client.groups.get(group_id)

    kwargs: dict[str, Any] = {"per_page": limit}
    if state and state != "all":
        kwargs["state"] = state

    iterations = group.iterations.list(**kwargs)
    return [IterationSummary.from_gitlab(i) for i in iterations]
