"""Query building utilities for filtering and sorting."""

from datetime import datetime
from typing import Any


def build_filters(
    state: str | None = None,
    author_id: int | None = None,
    author_username: str | None = None,
    assignee_id: int | None = None,
    labels: list[str] | None = None,
    milestone: str | None = None,
    search: str | None = None,
    created_after: datetime | str | None = None,
    created_before: datetime | str | None = None,
    updated_after: datetime | str | None = None,
    updated_before: datetime | str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a filter dict for GitLab API list operations.

    Only includes non-None values. Converts datetime objects to ISO format strings.

    Args:
        state: Filter by state (e.g., "opened", "closed", "locked", "merged")
        author_id: Filter by author user ID
        author_username: Filter by author username
        assignee_id: Filter by assignee user ID
        labels: Filter by labels (list of label names)
        milestone: Filter by milestone title
        search: Search in title and description
        created_after: Filter by creation date (ISO string or datetime)
        created_before: Filter by creation date (ISO string or datetime)
        updated_after: Filter by update date (ISO string or datetime)
        updated_before: Filter by update date (ISO string or datetime)
        **extra: Additional filters to include as-is

    Returns:
        Dictionary with only non-None filter values, ready for API call
    """
    filters: dict[str, Any] = {}

    # Add simple filters (None values excluded)
    if state is not None:
        filters["state"] = state
    if author_id is not None:
        filters["author_id"] = author_id
    if author_username is not None:
        filters["author_username"] = author_username
    if assignee_id is not None:
        filters["assignee_id"] = assignee_id
    if milestone is not None:
        filters["milestone"] = milestone
    if search is not None:
        filters["search"] = search

    # Handle labels (comma-separated string)
    if labels:
        filters["labels"] = ",".join(labels)

    # Convert datetime objects to ISO format strings
    if created_after is not None:
        filters["created_after"] = (
            created_after.isoformat() if isinstance(created_after, datetime) else created_after
        )
    if created_before is not None:
        filters["created_before"] = (
            created_before.isoformat() if isinstance(created_before, datetime) else created_before
        )
    if updated_after is not None:
        filters["updated_after"] = (
            updated_after.isoformat() if isinstance(updated_after, datetime) else updated_after
        )
    if updated_before is not None:
        filters["updated_before"] = (
            updated_before.isoformat() if isinstance(updated_before, datetime) else updated_before
        )

    # Add any extra filters that are not None
    for key, value in extra.items():
        if value is not None:
            filters[key] = value

    return filters


def build_sort(order_by: str | None = None, sort: str = "desc") -> dict[str, Any]:
    """Build sort parameters for GitLab API list operations.

    Args:
        order_by: Field to sort by (e.g., "created_at", "updated_at", "title")
        sort: Sort direction, "asc" or "desc" (default: "desc")

    Returns:
        Dictionary with sort parameters, empty if order_by is None

    Raises:
        ValueError: If sort is not "asc" or "desc"
    """
    if sort not in ("asc", "desc"):
        raise ValueError(f"sort must be 'asc' or 'desc', got '{sort}'")

    if order_by is None:
        return {}

    return {"order_by": order_by, "sort": sort}
