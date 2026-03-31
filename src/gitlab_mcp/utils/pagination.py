"""Pagination utilities for GitLab API list operations."""

from typing import Any


def paginate(
    manager: Any,
    per_page: int = 20,
    page: int = 1,
    **filters: Any,
) -> list[Any]:
    """Fetch results from a GitLab list endpoint.

    Makes a single API call to fetch up to per_page items from the given page.

    Args:
        manager: GitLab RESTManager (e.g., project.mergerequests)
        per_page: Number of items to return (default 20, max 100). GitLab API limit is 100.
        page: Page number to fetch (default 1, 1-indexed).
        **filters: Additional filters to pass to the list() call.
                  Examples: state="opened", author_id=123, labels="bug"

    Returns:
        List of items (up to per_page)

    Examples:
        >>> from gitlab_mcp.client import get_project
        >>> from gitlab_mcp.utils.pagination import paginate
        >>> project = get_project("mygroup/myproject")
        >>> mrs = paginate(project.mergerequests, state="opened", per_page=50)
        >>> issues = paginate(project.issues, labels="bug", per_page=10, page=2)
    """
    # Clamp per_page to valid GitLab API limits
    per_page = min(max(per_page, 1), 100)
    page = max(page, 1)

    return manager.list(page=page, per_page=per_page, **filters)
