"""Tests for GraphQL tools (no HTTP — invalid-input fast-paths)."""

import pytest
from gitlab_mcp.tools.graphql import execute_graphql, run_common_query, graphql_paginate

# These tools use httpx (not requests), so pook cannot intercept them.
# We test the error fast-paths that short-circuit before any HTTP call.

INVALID_QUERY = "{ }"  # no query/mutation/subscription keyword → fails validate_query


def test_execute_graphql_invalid_query(gitlab_token):
    """execute_graphql returns an error result for a syntactically invalid query."""
    result = execute_graphql(INVALID_QUERY)
    assert hasattr(result, "errors")
    assert result.errors is not None
    assert len(result.errors) > 0


def test_run_common_query_unknown_name(gitlab_token):
    """run_common_query returns an error result for an unknown query name."""
    result = run_common_query("nonexistent_query_name")
    assert hasattr(result, "errors")
    assert result.errors is not None
    assert len(result.errors) > 0


def test_graphql_paginate_invalid_query(gitlab_token):
    """graphql_paginate returns a PaginationResult with errors for an invalid query."""
    result = graphql_paginate(INVALID_QUERY)
    assert hasattr(result, "errors")
    assert result.errors is not None
    assert len(result.errors) > 0
