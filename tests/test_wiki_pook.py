"""Pook-based HTTP integration tests for wiki tools."""

import json
import pook
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.wiki import list_wiki_pages, get_wiki_page, search_wiki_pages
from gitlab_mcp.models.wiki import WikiPageSummary


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def test_list_wiki_pages():
    """Smoke test: list_wiki_pages returns a list of wiki page summaries."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/wikis",
        reply=200,
        response_json=load("wiki_pages_list.json"),
    )
    result = list_wiki_pages(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert hasattr(first, "slug")
    assert first.slug == "home"


def test_get_wiki_page():
    """Smoke test: get_wiki_page returns full wiki page detail."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/wikis/home",
        reply=200,
        response_json=load("wiki_page_single.json"),
    )
    result = get_wiki_page(PROJECT_ID, "home")
    assert result.slug == "home"
    assert hasattr(result, "content")
    assert result.content != ""


def test_search_wiki_pages():
    """Smoke test: search_wiki_pages filters pages by content match."""
    _mock_project()
    # search_wiki_pages lists all pages, then fetches each one to check content
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/wikis",
        reply=200,
        response_json=load("wiki_pages_list.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/wikis/home",
        reply=200,
        response_json=load("wiki_page_single.json"),
    )
    result = search_wiki_pages(PROJECT_ID, query="Welcome")
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0].slug == "home"
