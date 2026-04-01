"""Shared test fixtures and configuration."""

import json
import pytest
import pook
from pathlib import Path
import gitlab_mcp.client as _client_module
import gitlab_mcp.config as _config_module

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
MR_IID = 229854
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    """Load a JSON fixture by filename."""
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch):
    """Reset client and config singletons before each test."""
    monkeypatch.setattr(_client_module, "_client", None)
    monkeypatch.setattr(_config_module, "_config", None)


@pytest.fixture
def gitlab_token(monkeypatch):
    """Set a dummy GitLab token for pook-based tests."""
    monkeypatch.setenv("GITLAB_PERSONAL_ACCESS_TOKEN", "test-token")


@pytest.fixture(autouse=True)
def activate_pook():
    """Enable pook HTTP mocking for each test."""
    pook.on()
    yield
    pook.off()
    pook.reset()


@pytest.fixture
def mock_project(gitlab_token):
    """Mock the project GET endpoint (also sets a dummy auth token)."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}",
        reply=200,
        response_json=load("project.json"),
    )
