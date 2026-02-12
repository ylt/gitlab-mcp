"""Tests for issue tools."""

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
create_issue = get_tool_function("create_issue")
update_issue = get_tool_function("update_issue")
get_issue = get_tool_function("get_issue")
list_issues = get_tool_function("list_issues")


@pytest.fixture
def mock_project():
    """Create a mock GitLab project."""
    project = MagicMock()
    project.issues = MagicMock()
    return project


@pytest.fixture
def mock_issue():
    """Create a mock issue object."""
    issue = MagicMock()
    issue.iid = 1
    issue.title = "Test Issue"
    issue.description = "This is a test issue"
    issue.state = "opened"
    issue.author = {"username": "testuser"}
    issue.assignees = []
    issue.labels = ["bug"]
    issue.web_url = "https://gitlab.com/project/-/issues/1"
    issue.created_at = "2024-01-15T10:00:00Z"
    issue.updated_at = "2024-01-15T10:05:00Z"
    issue.confidential = False
    issue.weight = None
    issue.due_date = None
    return issue


class TestCreateIssue:
    """Test create_issue function."""

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_create_issue_basic(self, mock_get_project, mock_project, mock_issue):
        """Test basic issue creation without optional parameters."""
        mock_get_project.return_value = mock_project
        mock_project.issues.create.return_value = mock_issue

        result = create_issue("myproject", "Test Issue", "Description")

        assert result["iid"] == 1
        assert result["title"] == "Test Issue"
        mock_project.issues.create.assert_called_once()
        call_args = mock_project.issues.create.call_args[0][0]
        assert call_args["title"] == "Test Issue"
        assert call_args["description"] == "Description"
        assert "confidential" not in call_args
        assert "weight" not in call_args
        assert "due_date" not in call_args

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_create_issue_with_confidential(self, mock_get_project, mock_project, mock_issue):
        """Test issue creation with confidential flag."""
        mock_issue.confidential = True
        mock_get_project.return_value = mock_project
        mock_project.issues.create.return_value = mock_issue

        result = create_issue("myproject", "Secret Issue", confidential=True)

        assert result["confidential"] is True
        call_args = mock_project.issues.create.call_args[0][0]
        assert call_args["confidential"] is True

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_create_issue_with_weight(self, mock_get_project, mock_project, mock_issue):
        """Test issue creation with weight parameter."""
        mock_issue.weight = 5
        mock_get_project.return_value = mock_project
        mock_project.issues.create.return_value = mock_issue

        result = create_issue("myproject", "Weighted Issue", weight=5)

        assert result["weight"] == 5
        call_args = mock_project.issues.create.call_args[0][0]
        assert call_args["weight"] == 5

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_create_issue_with_due_date(self, mock_get_project, mock_project, mock_issue):
        """Test issue creation with due_date parameter."""
        mock_issue.due_date = "2024-12-31"
        mock_get_project.return_value = mock_project
        mock_project.issues.create.return_value = mock_issue

        result = create_issue("myproject", "Deadline Issue", due_date="2024-12-31")

        assert result["due_date"] == "2024-12-31"
        call_args = mock_project.issues.create.call_args[0][0]
        assert call_args["due_date"] == "2024-12-31"

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_create_issue_all_options(self, mock_get_project, mock_project, mock_issue):
        """Test issue creation with all optional parameters."""
        mock_issue.confidential = True
        mock_issue.weight = 3
        mock_issue.due_date = "2024-12-25"
        mock_issue.labels = ["bug", "urgent"]
        mock_get_project.return_value = mock_project
        mock_project.issues.create.return_value = mock_issue

        result = create_issue(
            "myproject",
            "Full Issue",
            description="Full test",
            labels="bug,urgent",
            confidential=True,
            weight=3,
            due_date="2024-12-25",
        )

        assert result["confidential"] is True
        assert result["weight"] == 3
        assert result["due_date"] == "2024-12-25"
        call_args = mock_project.issues.create.call_args[0][0]
        assert call_args["confidential"] is True
        assert call_args["weight"] == 3
        assert call_args["due_date"] == "2024-12-25"


class TestUpdateIssue:
    """Test update_issue function."""

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_update_issue_basic(self, mock_get_project, mock_project, mock_issue):
        """Test basic issue update without optional parameters."""
        mock_get_project.return_value = mock_project
        mock_project.issues.get.return_value = mock_issue

        update_issue("myproject", 1, title="Updated Title")

        assert mock_issue.title == "Updated Title"
        mock_issue.save.assert_called_once()

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_update_issue_confidential(self, mock_get_project, mock_project, mock_issue):
        """Test updating issue confidential flag."""
        mock_get_project.return_value = mock_project
        mock_project.issues.get.return_value = mock_issue

        update_issue("myproject", 1, confidential=True)

        assert mock_issue.confidential is True
        mock_issue.save.assert_called_once()

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_update_issue_weight(self, mock_get_project, mock_project, mock_issue):
        """Test updating issue weight."""
        mock_get_project.return_value = mock_project
        mock_project.issues.get.return_value = mock_issue

        update_issue("myproject", 1, weight=8)

        assert mock_issue.weight == 8
        mock_issue.save.assert_called_once()

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_update_issue_due_date(self, mock_get_project, mock_project, mock_issue):
        """Test updating issue due_date."""
        mock_get_project.return_value = mock_project
        mock_project.issues.get.return_value = mock_issue

        update_issue("myproject", 1, due_date="2025-06-30")

        assert mock_issue.due_date == "2025-06-30"
        mock_issue.save.assert_called_once()

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_update_issue_all_options(self, mock_get_project, mock_project, mock_issue):
        """Test updating issue with all optional parameters."""
        mock_get_project.return_value = mock_project
        mock_project.issues.get.return_value = mock_issue

        update_issue(
            "myproject",
            1,
            title="New Title",
            confidential=True,
            weight=2,
            due_date="2025-03-15",
        )

        assert mock_issue.title == "New Title"
        assert mock_issue.confidential is True
        assert mock_issue.weight == 2
        assert mock_issue.due_date == "2025-03-15"
        mock_issue.save.assert_called_once()

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_update_issue_confidential_false(self, mock_get_project, mock_project, mock_issue):
        """Test disabling confidential on an issue."""
        mock_issue.confidential = True
        mock_get_project.return_value = mock_project
        mock_project.issues.get.return_value = mock_issue

        update_issue("myproject", 1, confidential=False)

        assert mock_issue.confidential is False
        mock_issue.save.assert_called_once()


class TestGetIssue:
    """Test get_issue function."""

    @patch("gitlab_mcp.tools.issues.get_project")
    def test_get_issue_includes_new_fields(self, mock_get_project, mock_project, mock_issue):
        """Test that get_issue returns new fields."""
        mock_issue.confidential = True
        mock_issue.weight = 5
        mock_issue.due_date = "2024-12-31"
        mock_get_project.return_value = mock_project
        mock_project.issues.get.return_value = mock_issue

        result = get_issue("myproject", 1)

        assert result["confidential"] is True
        assert result["weight"] == 5
        assert result["due_date"] == "2024-12-31"


class TestListIssues:
    """Test list_issues function."""

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_includes_new_fields(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test that list_issues includes new fields in results."""
        mock_issue.confidential = True
        mock_issue.weight = 3
        mock_issue.due_date = "2025-01-15"
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        result = list_issues("myproject")

        assert len(result) == 1
        assert result[0]["confidential"] is True
        assert result[0]["weight"] == 3
        assert result[0]["due_date"] == "2025-01-15"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_state_filter(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test filtering issues by state."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", state="closed")

        # Verify paginate was called with state filter
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["state"] == "closed"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_author_filter(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test filtering issues by author username."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", author_username="testuser")

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["author_username"] == "testuser"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_assignee_filter(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test filtering issues by assignee username."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", assignee_username="assignee1")

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["assignee_username"] == "assignee1"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_labels_filter(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test filtering issues by labels."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", labels="bug,urgent")

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["labels"] == "bug,urgent"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_milestone_filter(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test filtering issues by milestone."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", milestone="v1.0")

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["milestone"] == "v1.0"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_search_filter(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test searching issues by text."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", search="database error")

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["search"] == "database error"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_date_filters(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test filtering issues by creation date range."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues(
            "myproject",
            created_after="2024-01-01T00:00:00Z",
            created_before="2024-12-31T23:59:59Z"
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["created_after"] == "2024-01-01T00:00:00Z"
        assert call_kwargs["created_before"] == "2024-12-31T23:59:59Z"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_sorting(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test sorting issues."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", order_by="updated_at", sort="asc")

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["order_by"] == "updated_at"
        assert call_kwargs["sort"] == "asc"

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_pagination(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test pagination parameters."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues("myproject", per_page=50)

        # Verify paginate was called with correct pagination params
        assert mock_paginate.call_args[0][0] == mock_project.issues
        assert mock_paginate.call_args[1]["per_page"] == 50

    @patch("gitlab_mcp.tools.issues.paginate")
    @patch("gitlab_mcp.tools.issues.get_project")
    def test_list_issues_with_all_filters(self, mock_get_project, mock_paginate, mock_project, mock_issue):
        """Test using all filters together."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_issue]

        list_issues(
            "myproject",
            per_page=25,
            state="opened",
            author_username="author1",
            assignee_username="assignee1",
            labels="bug,critical",
            milestone="v2.0",
            search="crash",
            created_after="2024-01-01",
            created_before="2024-12-31",
            order_by="priority",
            sort="desc"
        )

        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["per_page"] == 25
        assert call_kwargs["state"] == "opened"
        assert call_kwargs["author_username"] == "author1"
        assert call_kwargs["assignee_username"] == "assignee1"
        assert call_kwargs["labels"] == "bug,critical"
        assert call_kwargs["milestone"] == "v2.0"
        assert call_kwargs["search"] == "crash"
        assert call_kwargs["created_after"] == "2024-01-01"
        assert call_kwargs["created_before"] == "2024-12-31"
        assert call_kwargs["order_by"] == "priority"
        assert call_kwargs["sort"] == "desc"
