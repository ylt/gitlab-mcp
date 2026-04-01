"""Pook-based HTTP integration tests for project tools."""

import json
import pook
from pathlib import Path

from gitlab_mcp.tools.projects import (
    get_project,
    list_projects,
    list_project_members,
    list_group_projects,
    get_project_events,
)
from gitlab_mcp.models.projects import ProjectSummary

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
GROUP_ID = "9970"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


def test_get_project(mock_project):
    """Smoke test: get_project returns a ProjectSummary with the correct id."""
    result = get_project(PROJECT_ID)
    assert isinstance(result, ProjectSummary)
    assert result.id == int(PROJECT_ID)


def test_list_projects(gitlab_token):
    """Smoke test: list_projects returns a list of ProjectSummary objects."""
    pook.get(
        f"{BASE_URL}/projects",
        reply=200,
        response_json=load("project_list.json"),
    )
    result = list_projects()
    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], ProjectSummary)


def test_list_project_members(mock_project):
    """Smoke test: list_project_members returns a list of ProjectMember objects."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/members",
        reply=200,
        response_json=load("project_members.json"),
    )
    result = list_project_members(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "username")
    assert hasattr(result[0], "access_level")


def test_list_group_projects(gitlab_token):
    """Smoke test: list_group_projects returns a list of ProjectSummary objects."""
    pook.get(
        f"{BASE_URL}/groups/{GROUP_ID}",
        reply=200,
        response_json=load("group_single.json"),
    )
    pook.get(
        f"{BASE_URL}/groups/{GROUP_ID}/projects",
        reply=200,
        response_json=load("group_projects.json"),
    )
    result = list_group_projects(GROUP_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], ProjectSummary)


def test_get_project_events(mock_project):
    """Smoke test: get_project_events returns a list of event dicts."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/events",
        reply=200,
        response_json=load("project_events.json"),
    )
    result = get_project_events(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "id" in first
    assert "action" in first
    assert "summary" in first
