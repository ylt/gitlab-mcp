"""Configuration for GitLab MCP server."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Server configuration from environment variables."""

    gitlab_url: str
    token: str
    oauth_token: str | None = None
    session_cookie: str | None = None
    default_project_id: str | None = None
    read_only: bool = False
    retry_count: int = 3
    retry_backoff: float = 0.5
    timeout: int = 30
    disable_wiki: bool = False
    disable_releases: bool = False
    disable_graphql: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        url = os.environ.get("GITLAB_API_URL", "https://gitlab.com")
        # Strip /api/v4 suffix if present - python-gitlab adds it
        url = url.removesuffix("/api/v4")

        # Token priority: OAuth > Personal Access Token > Generic Token
        oauth_token = os.environ.get("GITLAB_OAUTH_TOKEN")
        token = os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")
        if not token:
            token = os.environ.get("GITLAB_TOKEN", "")

        session_cookie = os.environ.get("GITLAB_SESSION_COOKIE")

        # Parse retry configuration
        retry_count = int(os.environ.get("GITLAB_RETRY_COUNT", "3"))
        retry_backoff = float(os.environ.get("GITLAB_RETRY_BACKOFF", "0.5"))
        timeout = int(os.environ.get("GITLAB_TIMEOUT", "30"))

        # Parse feature toggles
        disable_wiki = os.environ.get("GITLAB_DISABLE_WIKI", "").lower() == "true"
        disable_releases = os.environ.get("GITLAB_DISABLE_RELEASES", "").lower() == "true"
        disable_graphql = os.environ.get("GITLAB_DISABLE_GRAPHQL", "").lower() == "true"

        return cls(
            gitlab_url=url,
            token=token,
            oauth_token=oauth_token,
            session_cookie=session_cookie,
            default_project_id=os.environ.get("GITLAB_PROJECT_ID"),
            read_only=os.environ.get("GITLAB_READ_ONLY_MODE", "").lower() == "true",
            retry_count=retry_count,
            retry_backoff=retry_backoff,
            timeout=timeout,
            disable_wiki=disable_wiki,
            disable_releases=disable_releases,
            disable_graphql=disable_graphql,
        )


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
