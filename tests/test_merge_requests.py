"""Tests for merge request tools."""

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
list_merge_requests = get_tool_function("list_merge_requests")
get_merge_request = get_tool_function("get_merge_request")
create_merge_request = get_tool_function("create_merge_request")


@pytest.fixture
def mock_project():
    """Create a mock GitLab project."""
    project = MagicMock()
    project.mergerequests = MagicMock()
    return project


@pytest.fixture
def mock_mr():
    """Create a mock merge request object."""
    mr = MagicMock()
    mr.iid = 1
    mr.title = "Test MR"
    mr.description = "This is a test MR"
    mr.state = "opened"
    mr.author = {"username": "testuser"}
    mr.assignees = []
    mr.reviewers = []
    mr.labels = ["feature"]
    mr.web_url = "https://gitlab.com/project/-/merge_requests/1"
    mr.created_at = "2024-01-15T10:00:00Z"
    mr.updated_at = "2024-01-15T10:05:00Z"
    mr.source_branch = "feature-branch"
    mr.target_branch = "main"
    mr.merge_status = "can_be_merged"
    mr.draft = False
    mr.work_in_progress = False
    mr.has_conflicts = False
    mr.blocking_discussions_resolved = True
    mr.upvotes = 2
    mr.downvotes = 0
    mr.head_pipeline = None
    mr.detailed_merge_status = None
    mr.approvals_required = 0
    mr.approvals_left = 0

    # Mock the approvals.get() method
    mock_approvals = MagicMock()
    mock_approvals.get.return_value = MagicMock(approvals_required=0, approvals_left=0)
    mr.approvals = mock_approvals
    return mr


class TestListMergeRequests:
    """Test list_merge_requests function with pagination and filtering."""

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_default_params(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test list_merge_requests with default parameters."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        result = list_merge_requests("myproject")

        # Verify paginate was called with correct parameters
        mock_paginate.assert_called_once()
        call_args = mock_paginate.call_args
        assert call_args[0][0] == mock_project.mergerequests
        assert call_args[1]["per_page"] == 20

        # Verify no filters applied by default
        assert "state" not in call_args[1]
        assert "author_username" not in call_args[1]

        # Verify response structure
        assert len(result) == 1
        assert result[0]["iid"] == 1
        assert result[0]["title"] == "Test MR"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_state_filter(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test filtering merge requests by state."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", state="closed")

        # Verify state filter was applied
        call_args = mock_paginate.call_args[1]
        assert call_args["state"] == "closed"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_author_filter(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test filtering merge requests by author username."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", author_username="johndoe")

        # Verify author filter was applied
        call_args = mock_paginate.call_args[1]
        assert call_args["author_username"] == "johndoe"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_assignee_filter(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test filtering merge requests by assignee username."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", assignee_username="janedoe")

        # Verify assignee filter was applied
        call_args = mock_paginate.call_args[1]
        assert call_args["assignee_username"] == "janedoe"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_labels_filter(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test filtering merge requests by labels."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", labels="bug,urgent")

        # Verify labels filter was applied (should be converted to list)
        call_args = mock_paginate.call_args[1]
        assert call_args["labels"] == "bug,urgent"  # build_filters converts to comma-separated

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_milestone_filter(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test filtering merge requests by milestone."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", milestone="v1.0")

        # Verify milestone filter was applied
        call_args = mock_paginate.call_args[1]
        assert call_args["milestone"] == "v1.0"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_search(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test searching merge requests by text."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", search="authentication")

        # Verify search filter was applied
        call_args = mock_paginate.call_args[1]
        assert call_args["search"] == "authentication"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_date_filters(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test filtering merge requests by creation date."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests(
            "myproject",
            created_after="2024-01-01T00:00:00Z",
            created_before="2024-12-31T23:59:59Z",
        )

        # Verify date filters were applied
        call_args = mock_paginate.call_args[1]
        assert call_args["created_after"] == "2024-01-01T00:00:00Z"
        assert call_args["created_before"] == "2024-12-31T23:59:59Z"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_sorting(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test sorting merge requests."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", order_by="updated_at", sort="asc")

        # Verify sort parameters were applied
        call_args = mock_paginate.call_args[1]
        assert call_args["order_by"] == "updated_at"
        assert call_args["sort"] == "asc"

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_custom_pagination(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test custom pagination parameters."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        list_merge_requests("myproject", per_page=50)

        # Verify pagination parameters were applied
        call_args = mock_paginate.call_args[1]
        assert call_args["per_page"] == 50

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_with_all_filters(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test list_merge_requests with all filter parameters."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = [mock_mr]

        result = list_merge_requests(
            "myproject",
            per_page=30,
            state="merged",
            author_username="alice",
            assignee_username="bob",
            labels="feature,priority",
            milestone="v2.0",
            search="refactor",
            created_after="2024-01-01T00:00:00Z",
            created_before="2024-06-30T23:59:59Z",
            order_by="created_at",
            sort="desc",
        )

        # Verify all parameters were applied
        call_args = mock_paginate.call_args[1]
        assert call_args["per_page"] == 30
        assert call_args["state"] == "merged"
        assert call_args["author_username"] == "alice"
        assert call_args["assignee_username"] == "bob"
        assert call_args["labels"] == "feature,priority"
        assert call_args["milestone"] == "v2.0"
        assert call_args["search"] == "refactor"
        assert call_args["created_after"] == "2024-01-01T00:00:00Z"
        assert call_args["created_before"] == "2024-06-30T23:59:59Z"
        assert call_args["order_by"] == "created_at"
        assert call_args["sort"] == "desc"

        # Verify result structure
        assert len(result) == 1
        assert isinstance(result[0], dict)

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_empty_result(self, mock_get_project, mock_paginate, mock_project):
        """Test list_merge_requests with no results."""
        mock_get_project.return_value = mock_project
        mock_paginate.return_value = []

        result = list_merge_requests("myproject", state="closed")

        # Verify empty list returned
        assert result == []
        mock_paginate.assert_called_once()

    @patch("gitlab_mcp.tools.merge_requests.paginate")
    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_list_merge_requests_multiple_results(self, mock_get_project, mock_paginate, mock_project, mock_mr):
        """Test list_merge_requests with multiple results."""
        mock_get_project.return_value = mock_project

        # Create multiple MRs
        mr1 = MagicMock()
        mr1.iid = 1
        mr1.title = "First MR"
        mr1.description = "First MR description"
        mr1.state = "opened"
        mr1.author = {"username": "user1"}
        mr1.assignees = []
        mr1.reviewers = []
        mr1.labels = []
        mr1.web_url = "https://gitlab.com/project/-/merge_requests/1"
        mr1.created_at = "2024-01-15T10:00:00Z"
        mr1.updated_at = "2024-01-15T10:05:00Z"
        mr1.source_branch = "feature-1"
        mr1.target_branch = "main"
        mr1.merge_status = "can_be_merged"
        mr1.draft = False
        mr1.work_in_progress = False
        mr1.has_conflicts = False
        mr1.blocking_discussions_resolved = True
        mr1.upvotes = 0
        mr1.downvotes = 0
        mr1.head_pipeline = None
        mr1.detailed_merge_status = None
        mr1.approvals_required = 0
        mr1.approvals_left = 0
        mock_approvals1 = MagicMock()
        mock_approvals1.get.return_value = MagicMock(approvals_required=0, approvals_left=0)
        mr1.approvals = mock_approvals1

        mr2 = MagicMock()
        mr2.iid = 2
        mr2.title = "Second MR"
        mr2.description = "Second MR description"
        mr2.state = "opened"
        mr2.author = {"username": "user2"}
        mr2.assignees = []
        mr2.reviewers = []
        mr2.labels = []
        mr2.web_url = "https://gitlab.com/project/-/merge_requests/2"
        mr2.created_at = "2024-01-16T10:00:00Z"
        mr2.updated_at = "2024-01-16T10:05:00Z"
        mr2.source_branch = "feature-2"
        mr2.target_branch = "main"
        mr2.merge_status = "can_be_merged"
        mr2.draft = False
        mr2.work_in_progress = False
        mr2.has_conflicts = False
        mr2.blocking_discussions_resolved = True
        mr2.upvotes = 0
        mr2.downvotes = 0
        mr2.head_pipeline = None
        mr2.detailed_merge_status = None
        mr2.approvals_required = 0
        mr2.approvals_left = 0
        mock_approvals2 = MagicMock()
        mock_approvals2.get.return_value = MagicMock(approvals_required=0, approvals_left=0)
        mr2.approvals = mock_approvals2

        mock_paginate.return_value = [mr1, mr2]

        result = list_merge_requests("myproject")

        # Verify multiple results returned
        assert len(result) == 2
        assert result[0]["iid"] == 1
        assert result[0]["title"] == "First MR"
        assert result[1]["iid"] == 2
        assert result[1]["title"] == "Second MR"


class TestGetMergeRequest:
    """Test get_merge_request function."""

    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_get_merge_request(self, mock_get_project, mock_project, mock_mr):
        """Test getting a single merge request."""
        mock_get_project.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr

        result = get_merge_request("myproject", 1)

        # Verify get was called with correct IID
        mock_project.mergerequests.get.assert_called_once_with(1)

        # Verify response structure
        assert result["iid"] == 1
        assert result["title"] == "Test MR"
        assert result["state"] == "opened"


class TestCreateMergeRequest:
    """Test create_merge_request function."""

    @patch("gitlab_mcp.tools.merge_requests.get_project")
    def test_create_merge_request_basic(self, mock_get_project, mock_project, mock_mr):
        """Test basic merge request creation."""
        mock_get_project.return_value = mock_project
        mock_project.mergerequests.create.return_value = mock_mr

        result = create_merge_request(
            "myproject",
            source_branch="feature",
            target_branch="main",
            title="New Feature",
        )

        # Verify create was called
        mock_project.mergerequests.create.assert_called_once()
        call_args = mock_project.mergerequests.create.call_args[0][0]
        assert call_args["source_branch"] == "feature"
        assert call_args["target_branch"] == "main"
        assert call_args["title"] == "New Feature"

        # Verify response
        assert result["iid"] == 1
        assert result["title"] == "Test MR"
