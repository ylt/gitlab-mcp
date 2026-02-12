"""Tests for pipeline tools."""

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
create_pipeline = get_tool_function("create_pipeline")
list_pipelines = get_tool_function("list_pipelines")
get_pipeline = get_tool_function("get_pipeline")
retry_pipeline = get_tool_function("retry_pipeline")
cancel_pipeline = get_tool_function("cancel_pipeline")
play_pipeline_job = get_tool_function("play_pipeline_job")
retry_pipeline_job = get_tool_function("retry_pipeline_job")
cancel_pipeline_job = get_tool_function("cancel_pipeline_job")


@pytest.fixture
def mock_project():
    """Create a mock GitLab project."""
    project = MagicMock()
    project.pipelines = MagicMock()
    project.jobs = MagicMock()
    return project


@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline object."""
    pipeline = MagicMock()
    pipeline.id = 123
    pipeline.status = "success"
    pipeline.ref = "main"
    pipeline.sha = "abc123def456"
    pipeline.web_url = "https://gitlab.com/project/-/pipelines/123"
    pipeline.created_at = "2024-01-15T10:00:00Z"
    pipeline.updated_at = "2024-01-15T10:05:00Z"
    pipeline.duration = 300
    pipeline.stages = ["build", "test", "deploy"]
    pipeline.failure_reason = None
    return pipeline


class TestCreatePipeline:
    """Test create_pipeline function."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_create_pipeline_basic(self, mock_get_project, mock_project, mock_pipeline):
        """Test basic pipeline creation without variables or description."""
        mock_get_project.return_value = mock_project
        mock_project.pipelines.create.return_value = mock_pipeline

        result = create_pipeline("myproject", "main")

        # Verify create was called with correct payload
        mock_project.pipelines.create.assert_called_once()
        call_args = mock_project.pipelines.create.call_args[0][0]
        assert call_args["ref"] == "main"
        assert "variables" not in call_args
        assert "description" not in call_args

        # Verify response structure
        assert result["id"] == 123
        assert result["status"] == "success"
        assert result["ref"] == "main"

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_create_pipeline_with_variables(self, mock_get_project, mock_project, mock_pipeline):
        """Test pipeline creation with variables."""
        mock_get_project.return_value = mock_project
        mock_project.pipelines.create.return_value = mock_pipeline

        variables = {"ENV": "production", "DEBUG": "false"}
        create_pipeline("myproject", "main", variables=variables)

        # Verify create was called with formatted variables
        mock_project.pipelines.create.assert_called_once()
        call_args = mock_project.pipelines.create.call_args[0][0]
        assert call_args["ref"] == "main"
        assert "variables" in call_args
        
        # Variables should be formatted as list of dicts with key/value
        expected_variables = [
            {"key": "ENV", "value": "production"},
            {"key": "DEBUG", "value": "false"},
        ]
        assert call_args["variables"] == expected_variables

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_create_pipeline_with_description(self, mock_get_project, mock_project, mock_pipeline):
        """Test pipeline creation with description."""
        mock_get_project.return_value = mock_project
        mock_project.pipelines.create.return_value = mock_pipeline

        create_pipeline(
            "myproject",
            "main",
            description="Manual pipeline for debugging"
        )

        # Verify create was called with description
        mock_project.pipelines.create.assert_called_once()
        call_args = mock_project.pipelines.create.call_args[0][0]
        assert call_args["ref"] == "main"
        assert call_args["description"] == "Manual pipeline for debugging"

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_create_pipeline_with_variables_and_description(
        self, mock_get_project, mock_project, mock_pipeline
    ):
        """Test pipeline creation with both variables and description."""
        mock_get_project.return_value = mock_project
        mock_project.pipelines.create.return_value = mock_pipeline

        variables = {"DEPLOY_TARGET": "staging"}
        description = "Staging deployment pipeline"
        
        create_pipeline(
            "myproject",
            "develop",
            variables=variables,
            description=description
        )

        # Verify create was called with both parameters
        mock_project.pipelines.create.assert_called_once()
        call_args = mock_project.pipelines.create.call_args[0][0]
        assert call_args["ref"] == "develop"
        assert call_args["description"] == description
        assert len(call_args["variables"]) == 1
        assert call_args["variables"][0] == {"key": "DEPLOY_TARGET", "value": "staging"}

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_create_pipeline_empty_variables_dict(self, mock_get_project, mock_project, mock_pipeline):
        """Test that empty variables dict is not added to payload."""
        mock_get_project.return_value = mock_project
        mock_project.pipelines.create.return_value = mock_pipeline

        create_pipeline("myproject", "main", variables={})

        # Verify empty dict doesn't add variables to payload
        call_args = mock_project.pipelines.create.call_args[0][0]
        assert "variables" not in call_args


class TestListPipelines:
    """Test list_pipelines function."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_list_pipelines_basic(self, mock_get_project, mock_project, mock_pipeline):
        """Test listing pipelines."""
        mock_get_project.return_value = mock_project
        mock_project.pipelines.list.return_value = [mock_pipeline]

        result = list_pipelines("myproject")

        # Verify list was called with correct limit
        mock_project.pipelines.list.assert_called_once()
        call_args = mock_project.pipelines.list.call_args[1]
        assert call_args["per_page"] == 20

        # Verify response structure
        assert len(result) == 1
        assert result[0]["id"] == 123


class TestGetPipeline:
    """Test get_pipeline function."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_get_pipeline(self, mock_get_project, mock_project, mock_pipeline):
        """Test getting a single pipeline."""
        mock_get_project.return_value = mock_project
        mock_project.pipelines.get.return_value = mock_pipeline

        result = get_pipeline("myproject", 123)

        # Verify get was called with correct ID
        mock_project.pipelines.get.assert_called_once_with(123)

        # Verify response structure
        assert result["id"] == 123
        assert result["status"] == "success"


class TestRetryPipeline:
    """Test retry_pipeline function."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_retry_pipeline(self, mock_get_project, mock_project, mock_pipeline):
        """Test retrying a failed pipeline."""
        mock_get_project.return_value = mock_project
        mock_pipeline.status = "failed"  # Set status to allow retry
        mock_pipeline.retry = MagicMock()
        mock_project.pipelines.get.return_value = mock_pipeline

        retry_pipeline("myproject", 123)

        # Verify retry was called
        mock_pipeline.retry.assert_called_once()

        # Verify get was called twice (initial + refresh)
        assert mock_project.pipelines.get.call_count == 2


class TestCancelPipeline:
    """Test cancel_pipeline function."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_cancel_pipeline(self, mock_get_project, mock_project, mock_pipeline):
        """Test canceling a running pipeline."""
        mock_get_project.return_value = mock_project
        mock_pipeline.status = "running"  # Set status to allow cancel
        mock_pipeline.cancel = MagicMock()
        mock_project.pipelines.get.return_value = mock_pipeline

        cancel_pipeline("myproject", 123)

        # Verify cancel was called
        mock_pipeline.cancel.assert_called_once()

        # Verify get was called twice (initial + refresh)
        assert mock_project.pipelines.get.call_count == 2


class TestRetryPipelineErrorHandling:
    """Test retry_pipeline graceful error handling."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_retry_pipeline_already_succeeded(self, mock_get_project, mock_project):
        """Test retry_pipeline skips retry if pipeline already succeeded."""
        mock_get_project.return_value = mock_project

        pipeline = MagicMock()
        pipeline.id = 456
        pipeline.status = "success"
        pipeline.retry = MagicMock()

        mock_project.pipelines.get.return_value = pipeline

        result = retry_pipeline("myproject", 456)

        # Verify retry was NOT called
        pipeline.retry.assert_not_called()

        # Verify graceful response
        assert result["status"] == "skipped"
        assert result["message"] == "Pipeline already succeeded; no retry needed"
        assert result["pipeline_id"] == 456
        assert result["current_status"] == "success"


class TestCancelPipelineErrorHandling:
    """Test cancel_pipeline graceful error handling."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_cancel_pipeline_already_completed(self, mock_get_project, mock_project):
        """Test cancel_pipeline skips cancel for completed pipelines."""
        mock_get_project.return_value = mock_project

        pipeline = MagicMock()
        pipeline.id = 789
        pipeline.status = "failed"
        pipeline.cancel = MagicMock()

        mock_project.pipelines.get.return_value = pipeline

        result = cancel_pipeline("myproject", 789)

        # Verify cancel was NOT called
        pipeline.cancel.assert_not_called()

        # Verify graceful response
        assert result["status"] == "skipped"
        assert result["message"] == "Pipeline already failed; cannot cancel"
        assert result["pipeline_id"] == 789
        assert result["current_status"] == "failed"

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_cancel_pipeline_multiple_completed_statuses(self, mock_get_project, mock_project):
        """Test cancel_pipeline handles various completed statuses."""
        mock_get_project.return_value = mock_project

        for status in ("success", "failed", "canceled", "skipped"):
            pipeline = MagicMock()
            pipeline.id = 999
            pipeline.status = status
            pipeline.cancel = MagicMock()

            mock_project.pipelines.get.return_value = pipeline

            result = cancel_pipeline("myproject", 999)

            # Verify cancel was NOT called for any completed status
            pipeline.cancel.assert_not_called()
            assert result["status"] == "skipped"
            assert result["current_status"] == status


class TestPlayJobErrorHandling:
    """Test play_pipeline_job graceful error handling."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_play_job_not_manual_or_skipped(self, mock_get_project, mock_project):
        """Test play_pipeline_job skips play for non-manual/skipped jobs."""
        mock_get_project.return_value = mock_project

        job = MagicMock()
        job.id = 111
        job.status = "success"
        job.play = MagicMock()

        mock_project.jobs.get.return_value = job

        result = play_pipeline_job("myproject", 111)

        # Verify play was NOT called
        job.play.assert_not_called()

        # Verify graceful response
        assert result["status"] == "skipped"
        assert result["message"] == "Job is success; only manual or skipped jobs can be played"
        assert result["job_id"] == 111
        assert result["current_status"] == "success"

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_play_job_valid_statuses(self, mock_get_project, mock_project):
        """Test play_pipeline_job allows manual and skipped jobs."""
        mock_get_project.return_value = mock_project

        for status in ("manual", "skipped"):
            job = MagicMock()
            job.id = 222
            job.name = "test_job"
            job.stage = "test"
            job.status = status
            job.web_url = "https://example.com/jobs/222"
            job.duration = None
            job.created_at = "2024-01-15T10:00:00Z"
            job.failure_reason = None
            job.retry_count = 0
            job.artifacts = None
            job.play = MagicMock()

            # Setup get to return job twice (initial + refresh)
            mock_project.jobs.get.side_effect = [job, job]

            result = play_pipeline_job("myproject", 222)

            # Verify play WAS called
            job.play.assert_called_once()
            # Result should be dict from JobSummary
            assert isinstance(result, dict)
            assert result["id"] == 222

            # Reset mock for next iteration
            mock_project.jobs.get.reset_mock()


class TestRetryJobErrorHandling:
    """Test retry_pipeline_job graceful error handling."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_retry_job_not_failed(self, mock_get_project, mock_project):
        """Test retry_pipeline_job skips retry for non-failed jobs."""
        mock_get_project.return_value = mock_project

        job = MagicMock()
        job.id = 333
        job.status = "success"
        job.retry = MagicMock()

        mock_project.jobs.get.return_value = job

        result = retry_pipeline_job("myproject", 333)

        # Verify retry was NOT called
        job.retry.assert_not_called()

        # Verify graceful response
        assert result["status"] == "skipped"
        assert result["message"] == "Job is success; only failed jobs can be retried"
        assert result["job_id"] == 333
        assert result["current_status"] == "success"

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_retry_job_various_non_failed_statuses(self, mock_get_project, mock_project):
        """Test retry_pipeline_job rejects various non-failed statuses."""
        mock_get_project.return_value = mock_project

        for status in ("pending", "running", "success", "canceled", "skipped"):
            job = MagicMock()
            job.id = 444
            job.status = status
            job.retry = MagicMock()

            mock_project.jobs.get.return_value = job

            result = retry_pipeline_job("myproject", 444)

            # Verify retry was NOT called
            job.retry.assert_not_called()
            assert result["status"] == "skipped"
            assert result["current_status"] == status

            # Reset mock for next iteration
            mock_project.jobs.get.reset_mock()


class TestCancelJobErrorHandling:
    """Test cancel_pipeline_job graceful error handling."""

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_cancel_job_already_completed(self, mock_get_project, mock_project):
        """Test cancel_pipeline_job skips cancel for completed jobs."""
        mock_get_project.return_value = mock_project

        job = MagicMock()
        job.id = 555
        job.status = "success"
        job.cancel = MagicMock()

        mock_project.jobs.get.return_value = job

        result = cancel_pipeline_job("myproject", 555)

        # Verify cancel was NOT called
        job.cancel.assert_not_called()

        # Verify graceful response
        assert result["status"] == "skipped"
        assert result["message"] == "Job already success; cannot cancel"
        assert result["job_id"] == 555
        assert result["current_status"] == "success"

    @patch("gitlab_mcp.tools.pipelines.get_project")
    def test_cancel_job_multiple_completed_statuses(self, mock_get_project, mock_project):
        """Test cancel_pipeline_job handles various completed statuses."""
        mock_get_project.return_value = mock_project

        for status in ("success", "failed", "canceled", "skipped"):
            job = MagicMock()
            job.id = 666
            job.status = status
            job.cancel = MagicMock()

            mock_project.jobs.get.return_value = job

            result = cancel_pipeline_job("myproject", 666)

            # Verify cancel was NOT called for any completed status
            job.cancel.assert_not_called()
            assert result["status"] == "skipped"
            assert result["current_status"] == status

            # Reset mock for next iteration
            mock_project.jobs.get.reset_mock()
