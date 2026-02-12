"""Namespace tools for GitLab."""

from typing import Any, cast
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_client
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_filters, build_sort
from gitlab_mcp.utils.cache import cached
from gitlab_mcp.models import NamespaceSummary, NamespaceVerification


@mcp.tool(
    annotations={
        "title": "List Namespaces",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_namespaces(
    per_page: int = 20,
    search: str | None = None,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[NamespaceSummary]:
    """List and search namespaces.

    Args:
        per_page: Items per page (default 20, max 100)
        search: Search query to filter namespaces by name/path
        order_by: Field to sort by (id, name, path, created_at)
        sort: Sort direction, "asc" or "desc" (default: "desc")
    """
    client = get_client()

    filters = build_filters(search=search)
    sort_params = build_sort(order_by=order_by, sort=sort)

    namespaces = paginate(
        client.namespaces,
        per_page=per_page,
        **filters,
        **sort_params,
    )

    return [NamespaceSummary.from_gitlab(ns) for ns in namespaces]


@mcp.tool(
    annotations={
        "title": "Get Namespace",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_namespace(namespace_id: int | str) -> NamespaceSummary:
    """Get namespace details.

    Args:
        namespace_id: Namespace ID or path (e.g., "mygroup" or numeric ID)
    """
    client = get_client()
    namespace = client.namespaces.get(namespace_id)
    return NamespaceSummary.from_gitlab(namespace)


@cached(ttl=300)
def _get_namespace_info(path: str) -> dict[str, Any] | None:
    """Get cached namespace info.

    Internal cached function - returns namespace info dict if found, None if not found.
    Does NOT handle suggestions.

    Args:
        path: Namespace path

    Returns:
        Dict with namespace details if found, None if not found
    """
    try:
        client = get_client()
        namespace = client.namespaces.get(path, lazy=True)
        namespace.reload()

        return cast(
            dict[str, Any],
            {
                "id": namespace.id,
                "name": namespace.name,
                "path": namespace.path,
                "full_path": namespace.full_path,
                "kind": namespace.kind,
            },
        )
    except Exception:
        return None


@mcp.tool(
    annotations={
        "title": "Verify Namespace",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def verify_namespace(path: str, suggest_similar: bool = False) -> NamespaceVerification:
    """Check if a namespace path exists.

    Args:
        path: Namespace path (e.g., "mygroup" or "parent-group/child-group")
        suggest_similar: If True and namespace not found, search for similar paths

    Returns:
        Dict with exists flag and namespace details if found, or error message if not found.
        If suggest_similar=True and not found, includes suggestions list.
    """
    # Use cached lookup for namespace verification
    namespace_info = _get_namespace_info(path)

    if namespace_info is not None:
        return NamespaceVerification.model_validate({"exists": True, **namespace_info})

    # Namespace not found
    result_data: dict[str, Any] = {
        "exists": False,
        "error": f"Namespace not found: {path}",
        "path": path,
    }

    # Search for similar namespaces if requested (NOT cached - always fresh search)
    if suggest_similar:
        try:
            client = get_client()
            # Search using the path as query
            search_results = client.namespaces.list(search=path, per_page=5)
            suggestions = [
                {
                    "id": ns.id,
                    "name": ns.name,
                    "path": ns.path,
                    "full_path": ns.full_path,
                    "kind": ns.kind,
                }
                for ns in search_results
            ]
            result_data["suggestions"] = suggestions
        except Exception:
            result_data["suggestions"] = []

    return NamespaceVerification.model_validate(result_data)
