"""GitLab API client wrapper."""

import gitlab
import requests
from typing import cast
from gitlab.v4.objects import Project
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from gitlab_mcp.config import get_config


# Global client instance
_client: gitlab.Gitlab | None = None


def _create_session_with_retries(
    retry_count: int = 3, backoff_factor: float = 0.5, timeout: int = 30
) -> requests.Session:
    """Create a requests Session with retry and connection pooling configuration.

    Args:
        retry_count: Number of retry attempts
        backoff_factor: Backoff factor for retries (delay = backoff_factor * (2 ** retry_number))
        timeout: Request timeout in seconds

    Returns:
        Configured requests Session
    """
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=retry_count,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
    )

    # Create adapter with retry strategy and connection pooling
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
    )

    # Mount adapter for both http and https
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def get_client() -> gitlab.Gitlab:
    """Get the GitLab API client with authentication and retry configuration."""
    global _client
    if _client is None:
        config = get_config()

        # Create session with retry and connection pooling
        session = _create_session_with_retries(
            retry_count=config.retry_count,
            backoff_factor=config.retry_backoff,
            timeout=config.timeout,
        )

        # Determine authentication method (priority: OAuth > Session Cookie > Personal Access Token)
        auth_kwargs = {}
        if config.oauth_token:
            auth_kwargs["oauth_token"] = config.oauth_token
        elif config.session_cookie:
            # For cookie-based auth, set the session cookie directly
            session.cookies.set("_gitlab_session", config.session_cookie)
        elif config.token:
            auth_kwargs["private_token"] = config.token

        _client = gitlab.Gitlab(
            url=config.gitlab_url,
            session=session,
            timeout=config.timeout,
            **auth_kwargs,
        )

    return _client


def get_project(project_id: str | None = None) -> Project:
    """Get a project by ID, falling back to default if configured."""
    config = get_config()
    pid = project_id or config.default_project_id
    if not pid:
        raise ValueError("project_id is required (no default configured)")
    return cast(Project, get_client().projects.get(pid))
