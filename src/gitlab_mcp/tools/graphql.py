"""GraphQL tool for advanced GitLab queries."""

from typing import Any

import httpx

from gitlab_mcp.config import get_config
from gitlab_mcp.models.graphql import GraphQLResponse, PaginationResult
from gitlab_mcp.server import mcp
from gitlab_mcp.utils.serialization import serialize_pydantic


# Common pre-built GraphQL queries
COMMON_QUERIES = {
    "current_user": """
        query {
            currentUser {
                id
                username
                name
                email
                publicEmail
                state
                webUrl
                avatarUrl
            }
        }
    """,
    "project_details": """
        query($path: ID!) {
            project(fullPath: $path) {
                id
                name
                description
                visibility
                webUrl
                sshUrlToRepo
                httpUrlToRepo
                starCount
                forksCount
                statistics {
                    commitCount
                    storageSize
                    repositorySize
                    wikiSize
                    lfsObjectsSize
                }
                languages {
                    name
                    share
                }
            }
        }
    """,
    "merge_request_details": """
        query($projectPath: ID!, $iid: String!) {
            project(fullPath: $projectPath) {
                mergeRequest(iid: $iid) {
                    id
                    iid
                    title
                    description
                    state
                    createdAt
                    updatedAt
                    mergedAt
                    author {
                        username
                        name
                    }
                    assignees {
                        nodes {
                            username
                            name
                        }
                    }
                    reviewers {
                        nodes {
                            username
                            name
                        }
                    }
                    approvedBy {
                        nodes {
                            username
                            name
                        }
                    }
                    sourceBranch
                    targetBranch
                    conflicts
                    mergeable
                    workInProgress
                    diffStatsSummary {
                        additions
                        deletions
                        changes
                    }
                }
            }
        }
    """,
    "issue_details": """
        query($projectPath: ID!, $iid: String!) {
            project(fullPath: $projectPath) {
                issue(iid: $iid) {
                    id
                    iid
                    title
                    description
                    state
                    createdAt
                    updatedAt
                    closedAt
                    author {
                        username
                        name
                    }
                    assignees {
                        nodes {
                            username
                            name
                        }
                    }
                    labels {
                        nodes {
                            title
                            color
                        }
                    }
                    milestone {
                        title
                        dueDate
                    }
                    webUrl
                }
            }
        }
    """,
    "pipeline_status": """
        query($projectPath: ID!, $sha: String!) {
            project(fullPath: $projectPath) {
                pipelines(sha: $sha, first: 1) {
                    nodes {
                        id
                        iid
                        status
                        createdAt
                        updatedAt
                        duration
                        coverage
                        user {
                            username
                            name
                        }
                        stages {
                            nodes {
                                name
                                status
                            }
                        }
                    }
                }
            }
        }
    """,
}


def validate_query(query: str) -> bool:
    """Basic validation that query has proper structure.

    Args:
        query: GraphQL query string to validate

    Returns:
        True if query appears valid, False otherwise
    """
    query = query.strip()

    if not query:
        return False

    # Check for query/mutation keyword
    if not any(keyword in query for keyword in ["query", "mutation", "subscription"]):
        return False

    # Check for balanced braces
    brace_count = 0
    for char in query:
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
        if brace_count < 0:
            return False

    return brace_count == 0


def _execute_graphql_internal(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Internal GraphQL execution logic.

    Args:
        query: GraphQL query string
        variables: Optional variables dict

    Returns:
        Raw GraphQL response dict
    """
    if not validate_query(query):
        return {"errors": [{"message": "Invalid query structure - check syntax and braces"}]}

    config = get_config()
    graphql_url = f"{config.gitlab_url}/api/graphql"

    headers = {
        "Content-Type": "application/json",
    }
    if config.token:
        headers["Authorization"] = f"Bearer {config.token}"

    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    response = httpx.post(
        graphql_url,
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()

    return response.json()


@mcp.tool(
    annotations={
        "title": "Execute GraphQL Query",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def execute_graphql(query: str, variables: dict[str, Any] | None = None) -> GraphQLResponse:
    """Execute a GitLab GraphQL query.

    Use this for advanced queries not covered by other tools.
    See https://docs.gitlab.com/ee/api/graphql/ for schema docs.

    Args:
        query: GraphQL query string
        variables: Optional variables dict for the query

    Returns:
        Query result with data and/or errors
    """
    result = _execute_graphql_internal(query, variables)
    return GraphQLResponse.model_validate(result, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "Run Common GraphQL Query",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def run_common_query(query_name: str, variables: dict[str, Any] | None = None) -> GraphQLResponse:
    """Run a pre-defined common GraphQL query.

    Available queries:
    - current_user: Get current authenticated user details
    - project_details: Get project info (requires path variable)
    - merge_request_details: Get MR details (requires projectPath and iid)
    - issue_details: Get issue details (requires projectPath and iid)
    - pipeline_status: Get pipeline status (requires projectPath and sha)

    Args:
        query_name: Name of the common query to run
        variables: Variables to pass to the query

    Returns:
        Query result with data and/or errors
    """
    if query_name not in COMMON_QUERIES:
        result = {
            "errors": [
                {
                    "message": f"Unknown query '{query_name}'. Available: {', '.join(COMMON_QUERIES.keys())}"
                }
            ]
        }
        return GraphQLResponse.model_validate(result, from_attributes=True)

    query = COMMON_QUERIES[query_name]
    result = _execute_graphql_internal(query, variables)
    return GraphQLResponse.model_validate(result, from_attributes=True)


@mcp.tool(
    annotations={
        "title": "GraphQL Query with Pagination",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
@serialize_pydantic
def graphql_paginate(
    query: str,
    variables: dict[str, Any] | None = None,
    cursor_path: str = "pageInfo.endCursor",
    has_next_path: str = "pageInfo.hasNextPage",
    max_pages: int = 10,
) -> PaginationResult:
    """Execute a GraphQL query with automatic cursor pagination.

    Automatically fetches all pages of results for queries using connection-based pagination.
    The query must use the 'after' variable for the cursor.

    Args:
        query: GraphQL query with pagination (must accept $after variable)
        variables: Initial variables dict for the query
        cursor_path: Dot-notation path to endCursor in response (default: pageInfo.endCursor)
        has_next_path: Dot-notation path to hasNextPage (default: pageInfo.hasNextPage)
        max_pages: Maximum pages to fetch (default: 10)

    Returns:
        Combined results with all_pages list and page_count
    """
    if variables is None:
        variables = {}

    all_results: list[dict[str, Any]] = []
    page_count = 0
    has_next = True

    while has_next and page_count < max_pages:
        result = _execute_graphql_internal(query, variables)

        if "errors" in result:
            return PaginationResult.model_validate(
                {
                    "errors": result["errors"],
                    "pages_fetched": page_count,
                    "partial_results": all_results,
                },
                from_attributes=True
            )

        all_results.append(result)
        page_count += 1

        # Navigate to cursor and hasNext using dot notation
        data: Any = result.get("data", {})

        # Get hasNextPage
        has_next_parts = has_next_path.split(".")
        has_next_value: Any = data
        for part in has_next_parts:
            if isinstance(has_next_value, dict):
                has_next_value = has_next_value.get(part)
            else:
                has_next_value = None
                break

        has_next = has_next_value is True

        if has_next:
            # Get endCursor
            cursor_parts = cursor_path.split(".")
            cursor_value: Any = data
            for part in cursor_parts:
                if isinstance(cursor_value, dict):
                    cursor_value = cursor_value.get(part)
                else:
                    cursor_value = None
                    break

            if cursor_value:
                variables["after"] = cursor_value
            else:
                has_next = False

    return PaginationResult.model_validate(
        {
            "all_pages": all_results,
            "page_count": page_count,
            "complete": not has_next or page_count < max_pages,
        },
        from_attributes=True
    )
