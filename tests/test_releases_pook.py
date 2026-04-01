"""Pook-based HTTP integration tests for release tools."""

import json
import pook
from pathlib import Path

from gitlab_mcp.tools.releases import list_releases, get_release, list_release_links
from gitlab_mcp.models.releases import ReleaseSummary

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"
RELEASE_TAG = "v18.10.0-ee"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


def test_list_releases(mock_project):
    """list_releases returns a list of ReleaseSummary objects."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/releases",
        reply=200,
        response_json=load("releases_list.json"),
    )
    result = list_releases(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert isinstance(first, ReleaseSummary)
    assert hasattr(first, "tag_name")
    assert first.tag_name == RELEASE_TAG


def test_get_release(mock_project):
    """get_release returns a ReleaseSummary with the correct tag_name."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/releases/{RELEASE_TAG}",
        reply=200,
        response_json=load("release_single.json"),
    )
    result = get_release(PROJECT_ID, RELEASE_TAG)
    assert isinstance(result, ReleaseSummary)
    assert result.tag_name == RELEASE_TAG


def test_list_release_links(mock_project):
    """list_release_links returns a list of release link objects."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/releases/{RELEASE_TAG}",
        reply=200,
        response_json=load("release_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/releases/{RELEASE_TAG}/assets/links",
        reply=200,
        response_json=load("release_links.json"),
    )
    result = list_release_links(PROJECT_ID, RELEASE_TAG)
    assert isinstance(result, list)
