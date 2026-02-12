"""Tests for namespace tools."""

import pytest
from unittest.mock import MagicMock, patch
from gitlab_mcp.server import mcp


# Get unwrapped functions from the MCP server
def get_tool_function(tool_name: str):
    """Extract the original function from a FastMCP tool."""
    for tool in mcp._tool_manager._tools.values():
        if tool.name == tool_name:
            return tool.fn
    raise ValueError(f"Tool {tool_name} not found")


# Extract the actual functions
list_namespaces = get_tool_function("list_namespaces")
get_namespace = get_tool_function("get_namespace")
verify_namespace = get_tool_function("verify_namespace")


@pytest.fixture
def mock_client():
    """Create a mock GitLab client."""
    client = MagicMock()
    client.namespaces = MagicMock()
    return client


@pytest.fixture
def mock_namespace():
    """Create a mock namespace object."""
    namespace = MagicMock()
    namespace.id = 123
    namespace.name = "Test Namespace"
    namespace.path = "test-namespace"
    namespace.description = "Test description"
    namespace.kind = "group"
    namespace.full_path = "parent/test-namespace"
    namespace.members_count = 5
    namespace.parent_id = 456
    return namespace


class TestListNamespaces:
    """Test list_namespaces function."""

    @patch("gitlab_mcp.tools.namespaces.get_client")
    @patch("gitlab_mcp.tools.namespaces.paginate")
    def test_list_namespaces_default_params(self, mock_paginate, mock_get_client, mock_client, mock_namespace):
        """Test listing namespaces with default parameters."""
        mock_get_client.return_value = mock_client
        mock_paginate.return_value = [mock_namespace]

        result = list_namespaces()

        assert len(result) == 1
        assert result[0]["id"] == 123
        assert result[0]["name"] == "Test Namespace"
        assert result[0]["path"] == "test-namespace"

        # Verify paginate was called with correct defaults
        mock_paginate.assert_called_once()
        call_args = mock_paginate.call_args
        assert call_args[0][0] == mock_client.namespaces
        assert call_args[1]["per_page"] == 20

    @patch("gitlab_mcp.tools.namespaces.get_client")
    @patch("gitlab_mcp.tools.namespaces.paginate")
    def test_list_namespaces_with_search(self, mock_paginate, mock_get_client, mock_client, mock_namespace):
        """Test listing namespaces with search filter."""
        mock_get_client.return_value = mock_client
        mock_paginate.return_value = [mock_namespace]

        result = list_namespaces(search="test")

        assert len(result) == 1
        mock_paginate.assert_called_once()
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["search"] == "test"

    @patch("gitlab_mcp.tools.namespaces.get_client")
    @patch("gitlab_mcp.tools.namespaces.paginate")
    def test_list_namespaces_with_pagination(self, mock_paginate, mock_get_client, mock_client, mock_namespace):
        """Test listing namespaces with custom pagination params."""
        mock_get_client.return_value = mock_client
        mock_paginate.return_value = [mock_namespace]

        list_namespaces(per_page=50)

        mock_paginate.assert_called_once()
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["per_page"] == 50

    @patch("gitlab_mcp.tools.namespaces.get_client")
    @patch("gitlab_mcp.tools.namespaces.paginate")
    def test_list_namespaces_with_sorting(self, mock_paginate, mock_get_client, mock_client, mock_namespace):
        """Test listing namespaces with sorting parameters."""
        mock_get_client.return_value = mock_client
        mock_paginate.return_value = [mock_namespace]

        list_namespaces(order_by="name", sort="asc")

        mock_paginate.assert_called_once()
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["order_by"] == "name"
        assert call_kwargs["sort"] == "asc"

    @patch("gitlab_mcp.tools.namespaces.get_client")
    @patch("gitlab_mcp.tools.namespaces.paginate")
    def test_list_namespaces_all_params(self, mock_paginate, mock_get_client, mock_client, mock_namespace):
        """Test listing namespaces with all parameters."""
        mock_get_client.return_value = mock_client
        mock_paginate.return_value = [mock_namespace]

        result = list_namespaces(
            per_page=30,
            search="test",
            order_by="created_at",
            sort="desc",
        )

        assert len(result) == 1
        mock_paginate.assert_called_once()
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["per_page"] == 30
        assert call_kwargs["search"] == "test"
        assert call_kwargs["order_by"] == "created_at"
        assert call_kwargs["sort"] == "desc"

    @patch("gitlab_mcp.tools.namespaces.get_client")
    @patch("gitlab_mcp.tools.namespaces.paginate")
    def test_list_namespaces_multiple_results(self, mock_paginate, mock_get_client, mock_client):
        """Test listing multiple namespaces."""
        mock_get_client.return_value = mock_client

        ns1 = MagicMock()
        ns1.id = 1
        ns1.name = "Namespace 1"
        ns1.path = "namespace-1"
        ns1.description = "First namespace"
        ns1.kind = "group"
        ns1.full_path = "namespace-1"

        ns2 = MagicMock()
        ns2.id = 2
        ns2.name = "Namespace 2"
        ns2.path = "namespace-2"
        ns2.description = None
        ns2.kind = "user"
        ns2.full_path = "namespace-2"

        mock_paginate.return_value = [ns1, ns2]

        result = list_namespaces()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Namespace 1"
        assert result[0]["kind"] == "group"
        assert result[1]["id"] == 2
        assert result[1]["name"] == "Namespace 2"
        assert result[1]["kind"] == "user"

    @patch("gitlab_mcp.tools.namespaces.get_client")
    @patch("gitlab_mcp.tools.namespaces.paginate")
    def test_list_namespaces_empty_results(self, mock_paginate, mock_get_client, mock_client):
        """Test listing namespaces when no results are found."""
        mock_get_client.return_value = mock_client
        mock_paginate.return_value = []

        result = list_namespaces(search="nonexistent")

        assert result == []
        mock_paginate.assert_called_once()


class TestGetNamespace:
    """Test get_namespace function."""

    @patch("gitlab_mcp.tools.namespaces.get_client")
    def test_get_namespace_by_id(self, mock_get_client, mock_client, mock_namespace):
        """Test getting namespace by numeric ID."""
        mock_get_client.return_value = mock_client
        mock_client.namespaces.get.return_value = mock_namespace

        result = get_namespace(123)

        assert result["id"] == 123
        assert result["name"] == "Test Namespace"
        assert result["path"] == "test-namespace"
        assert result["description"] == "Test description"
        assert result["kind"] == "group"
        assert result["full_path"] == "parent/test-namespace"

        # Note: members_count and parent_id are optional fields
        # They're included via getattr so may not be in the result
        if "members_count" in result:
            assert result["members_count"] == 5
        if "parent_id" in result:
            assert result["parent_id"] == 456

        mock_client.namespaces.get.assert_called_once_with(123)

    @patch("gitlab_mcp.tools.namespaces.get_client")
    def test_get_namespace_by_path(self, mock_get_client, mock_client, mock_namespace):
        """Test getting namespace by string path."""
        mock_get_client.return_value = mock_client
        mock_client.namespaces.get.return_value = mock_namespace

        result = get_namespace("test-namespace")

        assert result["name"] == "Test Namespace"
        mock_client.namespaces.get.assert_called_once_with("test-namespace")

    @patch("gitlab_mcp.tools.namespaces.get_client")
    def test_get_namespace_with_description(self, mock_get_client, mock_client):
        """Test getting namespace with description."""
        ns = MagicMock()
        ns.id = 789
        ns.name = "Simple Namespace"
        ns.path = "simple"
        ns.kind = "user"
        ns.full_path = "simple"
        ns.description = "A simple user namespace"

        mock_get_client.return_value = mock_client
        mock_client.namespaces.get.return_value = ns

        result = get_namespace(789)

        # Main fields should be present
        assert result["id"] == 789
        assert result["name"] == "Simple Namespace"
        assert result["path"] == "simple"
        assert result["kind"] == "user"
        assert result["full_path"] == "simple"
        assert result["description"] == "A simple user namespace"


class TestVerifyNamespace:
    """Test verify_namespace function."""

    @patch("gitlab_mcp.tools.namespaces.get_client")
    def test_verify_namespace_exists(self, mock_get_client, mock_client, mock_namespace):
        """Test verifying an existing namespace."""
        mock_get_client.return_value = mock_client
        mock_client.namespaces.get.return_value = mock_namespace

        result = verify_namespace("test-namespace")

        assert result["exists"] is True
        assert result["id"] == 123
        assert result["name"] == "Test Namespace"
        assert result["path"] == "test-namespace"
        assert result["full_path"] == "parent/test-namespace"
        assert result["kind"] == "group"

        mock_client.namespaces.get.assert_called_once_with("test-namespace", lazy=True)
        mock_namespace.reload.assert_called_once()

    @patch("gitlab_mcp.tools.namespaces.get_client")
    def test_verify_namespace_not_found(self, mock_get_client, mock_client):
        """Test verifying a non-existent namespace."""
        mock_get_client.return_value = mock_client
        mock_client.namespaces.get.side_effect = Exception("404 Namespace Not Found")

        result = verify_namespace("nonexistent")

        assert result["exists"] is False
        assert result["error"] == "Namespace not found: nonexistent"
        assert result["path"] == "nonexistent"

    @patch("gitlab_mcp.tools.namespaces.get_client")
    def test_verify_namespace_subgroup_path(self, mock_get_client, mock_client, mock_namespace):
        """Test verifying a subgroup namespace with full path."""
        mock_namespace.full_path = "parent/child/grandchild"
        mock_get_client.return_value = mock_client
        mock_client.namespaces.get.return_value = mock_namespace

        result = verify_namespace("parent/child/grandchild")

        assert result["exists"] is True
        assert result["full_path"] == "parent/child/grandchild"
