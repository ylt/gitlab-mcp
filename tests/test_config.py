"""Tests for configuration loading."""

import os
from gitlab_mcp.config import Config


class TestConfig:
    """Test configuration loading from environment variables."""

    def test_default_values(self, monkeypatch):
        """Test default configuration values."""
        # Clear all GitLab env vars
        for key in list(os.environ.keys()):
            if key.startswith("GITLAB_"):
                monkeypatch.delenv(key, raising=False)

        config = Config.from_env()
        assert config.gitlab_url == "https://gitlab.com"
        assert config.token == ""
        assert config.oauth_token is None
        assert config.session_cookie is None
        assert config.default_project_id is None
        assert config.read_only is False
        assert config.retry_count == 3
        assert config.retry_backoff == 0.5
        assert config.timeout == 30

    def test_custom_url(self, monkeypatch):
        """Test custom GitLab URL."""
        monkeypatch.setenv("GITLAB_API_URL", "https://gitlab.example.com")
        config = Config.from_env()
        assert config.gitlab_url == "https://gitlab.example.com"

    def test_url_strips_api_suffix(self, monkeypatch):
        """Test that /api/v4 suffix is stripped from URL."""
        monkeypatch.setenv("GITLAB_API_URL", "https://gitlab.example.com/api/v4")
        config = Config.from_env()
        assert config.gitlab_url == "https://gitlab.example.com"

    def test_personal_access_token(self, monkeypatch):
        """Test personal access token loading."""
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-pat-token")
        config = Config.from_env()
        assert config.token == "test-pat-token"

    def test_generic_token_fallback(self, monkeypatch):
        """Test fallback to GITLAB_TOKEN if GITLAB_PERSONAL_ACCESS_TOKEN not set."""
        monkeypatch.setenv("GITLAB_TOKEN", "test-generic-token")
        config = Config.from_env()
        assert config.token == "test-generic-token"

    def test_personal_access_token_priority(self, monkeypatch):
        """Test that GITLAB_PERSONAL_ACCESS_TOKEN takes priority over GITLAB_TOKEN."""
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-pat-token")
        monkeypatch.setenv("GITLAB_TOKEN", "test-generic-token")
        config = Config.from_env()
        assert config.token == "test-pat-token"

    def test_oauth_token(self, monkeypatch):
        """Test OAuth token loading."""
        monkeypatch.setenv("GITLAB_OAUTH_TOKEN", "test-oauth-token")
        config = Config.from_env()
        assert config.oauth_token == "test-oauth-token"

    def test_session_cookie(self, monkeypatch):
        """Test session cookie loading."""
        monkeypatch.setenv("GITLAB_SESSION_COOKIE", "test-session-cookie")
        config = Config.from_env()
        assert config.session_cookie == "test-session-cookie"

    def test_default_project_id(self, monkeypatch):
        """Test default project ID loading."""
        monkeypatch.setenv("GITLAB_PROJECT_ID", "123")
        config = Config.from_env()
        assert config.default_project_id == "123"

    def test_read_only_mode(self, monkeypatch):
        """Test read-only mode flag."""
        monkeypatch.setenv("GITLAB_READ_ONLY_MODE", "true")
        config = Config.from_env()
        assert config.read_only is True

    def test_read_only_mode_case_insensitive(self, monkeypatch):
        """Test read-only mode is case insensitive."""
        monkeypatch.setenv("GITLAB_READ_ONLY_MODE", "TRUE")
        config = Config.from_env()
        assert config.read_only is True

    def test_read_only_mode_false(self, monkeypatch):
        """Test read-only mode defaults to false."""
        monkeypatch.setenv("GITLAB_READ_ONLY_MODE", "false")
        config = Config.from_env()
        assert config.read_only is False

    def test_retry_count(self, monkeypatch):
        """Test custom retry count."""
        monkeypatch.setenv("GITLAB_RETRY_COUNT", "5")
        config = Config.from_env()
        assert config.retry_count == 5

    def test_retry_backoff(self, monkeypatch):
        """Test custom retry backoff factor."""
        monkeypatch.setenv("GITLAB_RETRY_BACKOFF", "1.0")
        config = Config.from_env()
        assert config.retry_backoff == 1.0

    def test_timeout(self, monkeypatch):
        """Test custom timeout."""
        monkeypatch.setenv("GITLAB_TIMEOUT", "60")
        config = Config.from_env()
        assert config.timeout == 60

    def test_all_custom_values(self, monkeypatch):
        """Test loading all custom configuration values."""
        monkeypatch.setenv("GITLAB_API_URL", "https://gitlab.example.com")
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-pat")
        monkeypatch.setenv("GITLAB_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("GITLAB_SESSION_COOKIE", "test-cookie")
        monkeypatch.setenv("GITLAB_PROJECT_ID", "456")
        monkeypatch.setenv("GITLAB_READ_ONLY_MODE", "true")
        monkeypatch.setenv("GITLAB_RETRY_COUNT", "10")
        monkeypatch.setenv("GITLAB_RETRY_BACKOFF", "2.0")
        monkeypatch.setenv("GITLAB_TIMEOUT", "120")

        config = Config.from_env()
        assert config.gitlab_url == "https://gitlab.example.com"
        assert config.token == "test-pat"
        assert config.oauth_token == "test-oauth"
        assert config.session_cookie == "test-cookie"
        assert config.default_project_id == "456"
        assert config.read_only is True
        assert config.retry_count == 10
        assert config.retry_backoff == 2.0
        assert config.timeout == 120
