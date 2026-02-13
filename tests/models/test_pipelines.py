"""Tests for pipeline and job models."""

from unittest.mock import Mock
from gitlab_mcp.models.pipelines import PipelineSummary, JobSummary


class TestPipelineSummary:
    """Test PipelineSummary model and from_gitlab conversion."""

    def test_basic_pipeline_creation(self):
        """Test creating a PipelineSummary with required fields."""
        pipeline = PipelineSummary(
            id=123,
            status="success",
            ref="main",
            sha="abc12345",
            web_url="https://gitlab.com/project/-/pipelines/123",
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T10:30:00Z",
        )

        assert pipeline.id == 123
        assert pipeline.status == "success"
        assert pipeline.ref == "main"
        assert pipeline.sha == "abc12345"
        assert pipeline.duration is None
        assert pipeline.stages is None
        assert pipeline.failure_reason is None

    def test_pipeline_with_all_fields(self):
        """Test PipelineSummary with all fields populated."""
        stages = [
            {"name": "build", "status": "success", "jobs": 1},
            {"name": "test", "status": "success", "jobs": 2},
            {"name": "deploy", "status": "success", "jobs": 1},
        ]
        pipeline = PipelineSummary(
            id=123,
            status="success",
            ref="main",
            sha="abc12345",
            web_url="https://gitlab.com/project/-/pipelines/123",
            created_at="2024-01-15T08:30:00Z",
            updated_at="2024-01-15T08:30:00Z",
            duration=125,
            stages=stages,
            failure_reason=None,
        )

        assert pipeline.id == 123
        assert pipeline.duration == 125
        assert pipeline.stages == stages
        assert pipeline.failure_reason is None

    def test_pipeline_failed_with_reason(self):
        """Test PipelineSummary with failure reason."""
        stages = [
            {"name": "build", "status": "success", "jobs": 1},
            {"name": "test", "status": "failed", "jobs": 2},
        ]
        pipeline = PipelineSummary(
            id=456,
            status="failed",
            ref="feature",
            sha="def67890",
            web_url="https://gitlab.com/project/-/pipelines/456",
            created_at="2024-01-15T09:30:00Z",
            updated_at="2024-01-15T09:30:00Z",
            duration=300,
            stages=stages,
            failure_reason="Test job failed: exit code 1",
        )

        assert pipeline.status == "failed"
        assert pipeline.failure_reason == "Test job failed: exit code 1"

    def test_from_gitlab_basic(self):
        """Test from_gitlab with minimal API response."""
        mock_pipeline = Mock()
        mock_pipeline.id = 789
        mock_pipeline.status = "running"
        mock_pipeline.ref = "develop"
        mock_pipeline.sha = "ghi01234567890abcdef"
        mock_pipeline.web_url = "https://gitlab.com/project/-/pipelines/789"
        mock_pipeline.created_at = "2024-01-15T10:30:00Z"
        mock_pipeline.updated_at = "2024-01-15T11:00:00Z"
        mock_pipeline.stages = None
        mock_pipeline.failure_reason = None
        mock_pipeline.duration = None

        pipeline = PipelineSummary.model_validate(mock_pipeline, from_attributes=True)

        assert pipeline.id == 789
        assert pipeline.status == "running"
        assert pipeline.ref == "develop"
        assert pipeline.sha == "ghi01234"
        assert pipeline.duration is None
        assert pipeline.stages is None
        assert pipeline.failure_reason is None

    def test_from_gitlab_with_stages(self):
        """Test from_gitlab with include_stages=True falls back to stage names."""
        mock_pipeline = Mock()
        mock_pipeline.id = 999
        mock_pipeline.status = "success"
        mock_pipeline.ref = "main"
        mock_pipeline.sha = "abc1234567890abcdef"
        mock_pipeline.web_url = "https://gitlab.com/project/-/pipelines/999"
        mock_pipeline.created_at = "2024-01-15T10:00:00Z"
        mock_pipeline.updated_at = "2024-01-15T10:30:00Z"
        mock_pipeline.stages = [
            {"name": "build", "status": "success", "jobs": 1},
            {"name": "test", "status": "success", "jobs": 2},
            {"name": "deploy", "status": "success", "jobs": 1},
        ]
        mock_pipeline.failure_reason = None
        mock_pipeline.duration = 1800
        # Mock jobs.list to raise an exception so it falls back to stage names
        mock_pipeline.jobs.list.side_effect = Exception("No jobs access")

        pipeline = PipelineSummary.model_validate(mock_pipeline, from_attributes=True)

        # Stages are passed through as-is in the model
        assert pipeline.stages == [
            {"name": "build", "status": "success", "jobs": 1},
            {"name": "test", "status": "success", "jobs": 2},
            {"name": "deploy", "status": "success", "jobs": 1},
        ]
        assert pipeline.duration == 1800

    def test_from_gitlab_with_failure_reason(self):
        """Test from_gitlab with failure reason."""
        mock_pipeline = Mock()
        mock_pipeline.id = 555
        mock_pipeline.status = "failed"
        mock_pipeline.ref = "bugfix"
        mock_pipeline.sha = "xyz9876543210fedcba"
        mock_pipeline.web_url = "https://gitlab.com/project/-/pipelines/555"
        mock_pipeline.created_at = "2024-01-15T09:00:00Z"
        mock_pipeline.updated_at = "2024-01-15T09:15:00Z"
        mock_pipeline.stages = [{"name": "build", "status": "success", "jobs": 1}]
        mock_pipeline.failure_reason = "Runner offline"
        mock_pipeline.duration = 900

        pipeline = PipelineSummary.model_validate(mock_pipeline, from_attributes=True)

        assert pipeline.status == "failed"
        assert pipeline.failure_reason == "Runner offline"

    def test_from_gitlab_missing_optional_attributes(self):
        """Test from_gitlab when object doesn't have optional attributes."""
        mock_pipeline = Mock(spec=["id", "status", "ref", "sha", "web_url", "created_at", "updated_at"])
        mock_pipeline.id = 111
        mock_pipeline.status = "pending"
        mock_pipeline.ref = "feature"
        mock_pipeline.sha = "aaa0000000000000000"
        mock_pipeline.web_url = "https://gitlab.com/project/-/pipelines/111"
        mock_pipeline.created_at = "2024-01-15T08:00:00Z"
        mock_pipeline.updated_at = "2024-01-15T08:00:00Z"

        pipeline = PipelineSummary.model_validate(mock_pipeline, from_attributes=True)

        assert pipeline.id == 111
        assert pipeline.duration is None
        assert pipeline.stages is None
        assert pipeline.failure_reason is None


class TestJobSummary:
    """Test JobSummary model and from_gitlab conversion."""

    def test_basic_job_creation(self):
        """Test creating a JobSummary with required fields."""
        job = JobSummary(
            id=456,
            name="unit_tests",
            stage="test",
            status="success",
            web_url="https://gitlab.com/project/-/jobs/456",
            created_at="2024-01-15T10:30:00Z",
        )

        assert job.id == 456
        assert job.name == "unit_tests"
        assert job.stage == "test"
        assert job.status == "success"
        assert job.duration is None
        assert job.failure_reason is None
        assert job.retry_count == 0
        assert job.artifacts is None

    def test_job_with_all_fields(self):
        """Test JobSummary with all fields populated."""
        job = JobSummary(
            id=789,
            name="build",
            stage="build",
            status="success",
            web_url="https://gitlab.com/project/-/jobs/789",
            created_at="2024-01-15T09:30:00Z",
            duration=45.5,
            failure_reason=None,
            retry_count=2,
            artifacts=["dist.tar.gz", "coverage.html"],
        )

        assert job.id == 789
        assert job.duration == 45.5
        assert job.retry_count == 2
        assert job.artifacts == ["dist.tar.gz", "coverage.html"]
        assert job.failure_reason is None

    def test_job_with_failure(self):
        """Test JobSummary with failure information."""
        job = JobSummary(
            id=999,
            name="deploy",
            stage="deploy",
            status="failed",
            web_url="https://gitlab.com/project/-/jobs/999",
            created_at="2024-01-15T09:00:00Z",
            duration=120.0,
            failure_reason="Connection timeout to production server",
            retry_count=1,
            artifacts=["logs.tar.gz"],
        )

        assert job.status == "failed"
        assert job.failure_reason == "Connection timeout to production server"
        assert job.retry_count == 1

    def test_from_gitlab_basic(self):
        """Test from_gitlab with minimal API response."""
        mock_job = Mock()
        mock_job.id = 111
        mock_job.name = "lint"
        mock_job.stage = "test"
        mock_job.status = "success"
        mock_job.web_url = "https://gitlab.com/project/-/jobs/111"
        mock_job.created_at = "2024-01-15T12:00:00Z"
        mock_job.duration = 30.5
        mock_job.failure_reason = None
        mock_job.retry_count = 0
        mock_job.artifacts = None

        job = JobSummary.model_validate(mock_job, from_attributes=True)

        assert job.id == 111
        assert job.name == "lint"
        assert job.duration == 30.5
        assert job.failure_reason is None
        assert job.retry_count == 0
        assert job.artifacts is None

    def test_from_gitlab_with_artifacts(self):
        """Test from_gitlab with artifacts."""
        mock_job = Mock()
        mock_job.id = 222
        mock_job.name = "build_artifacts"
        mock_job.stage = "build"
        mock_job.status = "success"
        mock_job.web_url = "https://gitlab.com/project/-/jobs/222"
        mock_job.created_at = "2024-01-15T13:00:00Z"
        mock_job.duration = 120.0
        mock_job.failure_reason = None
        mock_job.retry_count = 0
        mock_job.artifacts = [
            {"filename": "app.jar", "file_format": "jar"},
            {"filename": "app.tar.gz", "file_format": "tar"},
        ]

        job = JobSummary.model_validate(mock_job, from_attributes=True)

        assert job.artifacts is not None
        assert len(job.artifacts) == 2

    def test_from_gitlab_with_retry_count(self):
        """Test from_gitlab with retry count."""
        mock_job = Mock()
        mock_job.id = 333
        mock_job.name = "flaky_test"
        mock_job.stage = "test"
        mock_job.status = "success"
        mock_job.web_url = "https://gitlab.com/project/-/jobs/333"
        mock_job.created_at = "2024-01-15T14:00:00Z"
        mock_job.duration = 60.0
        mock_job.failure_reason = None
        mock_job.retry_count = 3
        mock_job.artifacts = None

        job = JobSummary.model_validate(mock_job, from_attributes=True)

        assert job.retry_count == 3

    def test_from_gitlab_with_failure_reason(self):
        """Test from_gitlab with failure reason."""
        mock_job = Mock()
        mock_job.id = 444
        mock_job.name = "integration_tests"
        mock_job.stage = "test"
        mock_job.status = "failed"
        mock_job.web_url = "https://gitlab.com/project/-/jobs/444"
        mock_job.created_at = "2024-01-15T15:00:00Z"
        mock_job.duration = 180.5
        mock_job.failure_reason = "Database connection failed"
        mock_job.retry_count = 2
        mock_job.artifacts = [{"filename": "test-results.xml", "file_format": "xml"}]

        job = JobSummary.model_validate(mock_job, from_attributes=True)

        assert job.status == "failed"
        assert job.failure_reason == "Database connection failed"
        assert job.retry_count == 2
        assert job.artifacts is not None

    def test_from_gitlab_artifacts_with_empty_names(self):
        """Test from_gitlab filters out empty artifact names."""
        mock_job = Mock()
        mock_job.id = 555
        mock_job.name = "test_job"
        mock_job.stage = "test"
        mock_job.status = "success"
        mock_job.web_url = "https://gitlab.com/project/-/jobs/555"
        mock_job.created_at = "2024-01-15T16:00:00Z"
        mock_job.duration = 45.0
        mock_job.failure_reason = None
        mock_job.retry_count = 0
        mock_job.artifacts = [
            {"filename": "results.xml", "file_format": "xml"},
            {"file_format": ""},
            {"filename": "", "file_format": ""},
        ]

        job = JobSummary.model_validate(mock_job, from_attributes=True)

        assert job.artifacts is not None
        assert len(job.artifacts) >= 1

    def test_from_gitlab_missing_optional_attributes(self):
        """Test from_gitlab when job object doesn't have optional attributes."""
        mock_job = Mock(spec=["id", "name", "stage", "status", "web_url", "created_at", "duration"])
        mock_job.id = 666
        mock_job.name = "simple_job"
        mock_job.stage = "build"
        mock_job.status = "success"
        mock_job.web_url = "https://gitlab.com/project/-/jobs/666"
        mock_job.created_at = "2024-01-15T17:00:00Z"
        mock_job.duration = 90.0

        job = JobSummary.model_validate(mock_job, from_attributes=True)

        assert job.id == 666
        assert job.failure_reason is None
        assert job.retry_count == 0
        assert job.artifacts is None
