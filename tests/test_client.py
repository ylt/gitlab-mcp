"""Tests for GitLab client configuration."""

import pytest
import requests
from unittest.mock import patch
from gitlab_mcp.client import get_client, _create_session_with_retries


@pytest.fixture(autouse=True)
def reset_client():
    """Reset global client instance before each test."""
    import gitlab_mcp.client as client_module
    client_module._client = None
    yield
    client_module._client = None


@pytest.fixture(autouse=True)
def reset_config():
    """Reset global config instance before each test."""
    import gitlab_mcp.config as config_module
    config_module._config = None
    yield
    config_module._config = None


class TestSessionCreation:
    """Test session creation with retry and pooling configuration."""

    def test_default_session_configuration(self):
        """Test session created with default retry configuration."""
        session = _create_session_with_retries()
        assert isinstance(session, requests.Session)

        # Check that adapters are mounted
        assert "http://" in session.adapters
        assert "https://" in session.adapters

    def test_custom_retry_count(self):
        """Test session with custom retry count."""
        session = _create_session_with_retries(retry_count=5)
        adapter = session.get_adapter("https://")
        assert adapter.max_retries.total == 5

    def test_custom_backoff_factor(self):
        """Test session with custom backoff factor."""
        session = _create_session_with_retries(backoff_factor=1.0)
        adapter = session.get_adapter("https://")
        assert adapter.max_retries.backoff_factor == 1.0

    def test_retry_on_status_codes(self):
        """Test that retry is configured for common error status codes."""
        session = _create_session_with_retries()
        adapter = session.get_adapter("https://")
        retry = adapter.max_retries

        expected_status_codes = {429, 500, 502, 503, 504}
        assert set(retry.status_forcelist) == expected_status_codes

    def test_retry_allowed_methods(self):
        """Test that retry is configured for all HTTP methods."""
        session = _create_session_with_retries()
        adapter = session.get_adapter("https://")
        retry = adapter.max_retries

        expected_methods = ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        assert set(retry.allowed_methods) == set(expected_methods)

    def test_connection_pooling(self):
        """Test connection pooling configuration."""
        session = _create_session_with_retries()
        adapter = session.get_adapter("https://")

        # HTTPAdapter should have pool configuration
        assert hasattr(adapter, "_pool_connections")
        assert hasattr(adapter, "_pool_maxsize")


class TestClientAuthentication:
    """Test GitLab client authentication methods."""

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_personal_access_token_auth(self, mock_gitlab, monkeypatch):
        """Test client creation with personal access token."""
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-pat-token")

        get_client()

        # Verify Gitlab was called with private_token
        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert call_kwargs["private_token"] == "test-pat-token"
        assert "oauth_token" not in call_kwargs

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_oauth_token_auth(self, mock_gitlab, monkeypatch):
        """Test client creation with OAuth token (takes priority)."""
        monkeypatch.setenv("GITLAB_OAUTH_TOKEN", "test-oauth-token")
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-pat-token")

        get_client()

        # Verify Gitlab was called with oauth_token
        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert call_kwargs["oauth_token"] == "test-oauth-token"
        assert "private_token" not in call_kwargs

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_session_cookie_auth(self, mock_gitlab, monkeypatch):
        """Test client creation with session cookie."""
        monkeypatch.setenv("GITLAB_SESSION_COOKIE", "test-session-cookie")

        get_client()

        # Verify session was configured with cookie
        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        session = call_kwargs["session"]
        assert session.cookies.get("_gitlab_session") == "test-session-cookie"
        assert "private_token" not in call_kwargs
        assert "oauth_token" not in call_kwargs

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_auth_priority_oauth_over_cookie(self, mock_gitlab, monkeypatch):
        """Test that OAuth token takes priority over session cookie."""
        monkeypatch.setenv("GITLAB_OAUTH_TOKEN", "test-oauth-token")
        monkeypatch.setenv("GITLAB_SESSION_COOKIE", "test-session-cookie")

        get_client()

        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert call_kwargs["oauth_token"] == "test-oauth-token"

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_auth_priority_cookie_over_pat(self, mock_gitlab, monkeypatch):
        """Test that session cookie takes priority over personal access token."""
        monkeypatch.setenv("GITLAB_SESSION_COOKIE", "test-session-cookie")
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-pat-token")

        get_client()

        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        session = call_kwargs["session"]
        assert session.cookies.get("_gitlab_session") == "test-session-cookie"
        assert "private_token" not in call_kwargs


class TestClientConfiguration:
    """Test GitLab client retry and timeout configuration."""

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_default_timeout(self, mock_gitlab, monkeypatch):
        """Test client created with default timeout."""
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-token")

        get_client()

        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert call_kwargs["timeout"] == 30

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_custom_timeout(self, mock_gitlab, monkeypatch):
        """Test client created with custom timeout."""
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("GITLAB_TIMEOUT", "60")

        get_client()

        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert call_kwargs["timeout"] == 60

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_session_with_retries(self, mock_gitlab, monkeypatch):
        """Test that client is created with a session configured for retries."""
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("GITLAB_RETRY_COUNT", "5")
        monkeypatch.setenv("GITLAB_RETRY_BACKOFF", "1.0")

        get_client()

        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        session = call_kwargs["session"]

        # Verify session has retry configuration
        adapter = session.get_adapter("https://")
        assert adapter.max_retries.total == 5
        assert adapter.max_retries.backoff_factor == 1.0

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_url_configuration(self, mock_gitlab, monkeypatch):
        """Test client created with correct GitLab URL."""
        monkeypatch.setenv("GITLAB_API_URL", "https://gitlab.example.com")
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-token")

        get_client()

        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert call_kwargs["url"] == "https://gitlab.example.com"


class TestClientSingleton:
    """Test client singleton behavior."""

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_client_singleton(self, mock_gitlab, monkeypatch):
        """Test that get_client returns the same instance on repeated calls."""
        monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-token")

        client1 = get_client()
        client2 = get_client()

        # Should only create client once
        assert mock_gitlab.call_count == 1
        assert client1 is client2


class TestBackwardsCompatibility:
    """Test backwards compatibility with existing token configuration."""

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_legacy_gitlab_token(self, mock_gitlab, monkeypatch):
        """Test that GITLAB_TOKEN still works for backwards compatibility."""
        monkeypatch.setenv("GITLAB_TOKEN", "test-legacy-token")

        get_client()

        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert call_kwargs["private_token"] == "test-legacy-token"

    @patch("gitlab_mcp.client.gitlab.Gitlab")
    def test_no_token_no_crash(self, mock_gitlab, monkeypatch):
        """Test that client can be created even without a token."""
        # Clear all token env vars
        for key in ["GITLAB_PERSONAL_ACCESS_TOKEN", "GITLAB_TOKEN", "GITLAB_OAUTH_TOKEN", "GITLAB_SESSION_COOKIE"]:
            monkeypatch.delenv(key, raising=False)

        get_client()

        # Should still create client, just without auth
        mock_gitlab.assert_called_once()
        call_kwargs = mock_gitlab.call_args[1]
        assert "private_token" not in call_kwargs or call_kwargs.get("private_token") == ""
        assert "oauth_token" not in call_kwargs
