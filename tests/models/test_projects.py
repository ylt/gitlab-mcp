"""Tests for project models."""

from datetime import datetime, timezone
from unittest.mock import MagicMock


from gitlab_mcp.models.projects import ProjectSummary


class TestProjectSummary:
    """Test ProjectSummary model."""

    def test_from_gitlab_with_all_fields(self):
        """Test creating ProjectSummary from gitlab project with all fields populated."""
        # Create mock project with all fields
        iso_time = "2024-01-15T10:30:00Z"

        class MockProject:
            id = 123
            path_with_namespace = "group/project"
            name = "Test Project"
            description = "A test project"
            web_url = "https://gitlab.com/group/project"
            default_branch = "main"
            visibility = "public"
            created_at = iso_time
            star_count = 42
            forks_count = 8
            last_activity_at = iso_time
            open_issues_count = 5

        # Create ProjectSummary from mock
        result = ProjectSummary.model_validate(MockProject(), from_attributes=True)

        # Verify all fields
        assert result.id == 123
        assert result.path_with_namespace == "group/project"
        assert result.name == "Test Project"
        assert result.description == "A test project"
        assert result.web_url == "https://gitlab.com/group/project"
        assert result.default_branch == "main"
        assert result.visibility == "public"
        assert result.star_count == 42
        assert result.forks_count == 8
        assert result.open_issues_count == 5
        # created_at and last_activity_at are converted to relative_time strings
        assert isinstance(result.created_at, str)
        assert isinstance(result.last_activity_at, str)

    def test_from_gitlab_with_missing_fields(self):
        """Test creating ProjectSummary from gitlab project with missing optional fields."""
        # Create a proper mock with defaults for optional fields
        class MockProject:
            id = 456
            path_with_namespace = "other/repo"
            name = "Another Project"
            description = None  # Will be converted to ""
            web_url = "https://gitlab.com/other/repo"
            default_branch = None  # Will be converted to "main"
            visibility = "private"
            created_at = "2024-01-15T10:30:00Z"
            star_count = 0  # Default
            forks_count = 0  # Default
            open_issues_count = 0  # Default
            last_activity_at = None  # Will convert to "unknown"

        mock_project = MockProject()

        # Create ProjectSummary from mock
        result = ProjectSummary.model_validate(mock_project, from_attributes=True)

        # Verify defaults for missing fields
        assert result.id == 456
        assert result.path_with_namespace == "other/repo"
        assert result.name == "Another Project"
        assert result.description is None  # None is acceptable, serializer converts to "" on output
        assert result.default_branch == "main"  # Default fallback
        assert result.star_count == 0
        assert result.forks_count == 0
        assert result.open_issues_count == 0
        # Note: last_activity_at defaults to "unknown" when not provided
        assert result.last_activity_at == "unknown"

    def test_star_count_default(self):
        """Test that star_count defaults to 0."""
        project = ProjectSummary(
            id=1,
            path_with_namespace="test/project",
            name="Test",
            web_url="https://gitlab.com/test/project",
            default_branch="main",
            visibility="public",
            created_at="2024-01-15T10:30:00Z",
        )
        assert project.star_count == 0

    def test_fork_count_default(self):
        """Test that forks_count defaults to 0."""
        project = ProjectSummary(
            id=1,
            path_with_namespace="test/project",
            name="Test",
            description="Test project",
            web_url="https://gitlab.com/test/project",
            default_branch="main",
            visibility="public",
            created_at="2024-01-15T10:30:00Z",
        )
        assert project.forks_count == 0

    def test_open_issues_count_default(self):
        """Test that open_issues_count defaults to 0."""
        project = ProjectSummary(
            id=1,
            path_with_namespace="test/project",
            name="Test",
            web_url="https://gitlab.com/test/project",
            default_branch="main",
            visibility="public",
            created_at="2024-01-15T10:30:00Z",
        )
        assert project.open_issues_count == 0

    def test_last_activity_at_default(self):
        """Test that last_activity_at defaults to 'unknown' when not provided."""
        project = ProjectSummary(
            id=1,
            path_with_namespace="test/project",
            name="Test",
            web_url="https://gitlab.com/test/project",
            default_branch="main",
            visibility="public",
            created_at="2024-01-15T10:30:00Z",
        )
        assert project.last_activity_at == "unknown"

    def test_from_gitlab_preserves_star_count(self):
        """Test that star_count is preserved from gitlab object."""

        class MockProject:
            id = 1
            path_with_namespace = "test/project"
            name = "Test"
            description = "Test project"
            web_url = "https://gitlab.com/test/project"
            default_branch = "main"
            visibility = "public"
            created_at = "2024-01-15T10:30:00Z"
            star_count = 15

        result = ProjectSummary.model_validate(MockProject(), from_attributes=True)
        assert result.star_count == 15

    def test_from_gitlab_preserves_fork_count(self):
        """Test that fork_count is preserved from gitlab object."""

        class MockProject:
            id = 1
            path_with_namespace = "test/project"
            name = "Test"
            description = "Test project"
            web_url = "https://gitlab.com/test/project"
            default_branch = "main"
            visibility = "public"
            created_at = "2024-01-15T10:30:00Z"
            forks_count = 3

        result = ProjectSummary.model_validate(MockProject(), from_attributes=True)
        assert result.forks_count == 3

    def test_from_gitlab_preserves_open_issues_count(self):
        """Test that open_issues_count is preserved from gitlab object."""

        class MockProject:
            id = 1
            path_with_namespace = "test/project"
            name = "Test"
            description = "Test project"
            web_url = "https://gitlab.com/test/project"
            default_branch = "main"
            visibility = "public"
            created_at = "2024-01-15T10:30:00Z"
            open_issues_count = 12

        result = ProjectSummary.model_validate(MockProject(), from_attributes=True)
        assert result.open_issues_count == 12

    def test_from_gitlab_last_activity_uses_relative_time(self):
        """Test that last_activity_at uses relative_time formatting."""
        class MockProject:
            id = 1
            path_with_namespace = "test/project"
            name = "Test"
            description = "Test project"
            web_url = "https://gitlab.com/test/project"
            default_branch = "main"
            visibility = "public"
            created_at = "2024-01-15T10:30:00Z"
            last_activity_at = "2024-01-13T10:30:00Z"  # 2 days before

        result = ProjectSummary.model_validate(MockProject(), from_attributes=True)
        # The relative_time function produces a relative string
        assert isinstance(result.last_activity_at, str)
        # Should be relative time format (not ISO string anymore)
        assert "T" not in result.last_activity_at or result.last_activity_at == "unknown"
