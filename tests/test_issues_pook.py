"""Pook-based HTTP integration tests for issue tools."""

import json
import pook
from pathlib import Path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.issues import (
    list_issues,
    get_issue,
    list_issue_links,
    get_issue_link,
    list_related_merge_requests,
    get_time_stats,
    my_issues,
)

ISSUE_IID = 595528  # from issue_single.json


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def test_list_issues():
    """Smoke test: list_issues returns a list of issue summaries."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues",
        reply=200,
        response_json=load("issue_list.json"),
    )
    results = list_issues(PROJECT_ID)
    assert isinstance(results, list)
    assert len(results) == 2
    first = results[0]
    assert hasattr(first, "iid")
    assert hasattr(first, "title")
    assert hasattr(first, "state")


def test_get_issue():
    """Smoke test: get_issue returns a single issue summary."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}",
        reply=200,
        response_json=load("issue_single.json"),
    )
    result = get_issue(PROJECT_ID, ISSUE_IID)
    assert result.iid == ISSUE_IID
    assert hasattr(result, "title")
    assert hasattr(result, "state")


ISSUE_LINK_ID = 999  # from issue_links.json


def test_list_issue_links():
    """Smoke test: list_issue_links returns a list of IssueLink objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}",
        reply=200,
        response_json=load("issue_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}/links",
        reply=200,
        response_json=load("issue_links.json"),
    )
    result = list_issue_links(PROJECT_ID, ISSUE_IID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "id")


def test_get_issue_link():
    """Smoke test: get_issue_link returns the matching IssueLink by id."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}",
        reply=200,
        response_json=load("issue_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}/links",
        reply=200,
        response_json=load("issue_links.json"),
    )
    result = get_issue_link(PROJECT_ID, ISSUE_IID, ISSUE_LINK_ID)
    assert result.id == ISSUE_LINK_ID


def test_list_related_merge_requests():
    """Smoke test: list_related_merge_requests returns a list of RelatedMergeRequest objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}",
        reply=200,
        response_json=load("issue_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}/related_merge_requests",
        reply=200,
        response_json=load("related_merge_requests.json"),
    )
    result = list_related_merge_requests(PROJECT_ID, ISSUE_IID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "iid")


def test_get_time_stats():
    """Smoke test: get_time_stats returns an IssueTimeStats object."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}",
        reply=200,
        response_json=load("issue_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}/time_stats",
        reply=200,
        response_json=load("issue_time_stats.json"),
    )
    result = get_time_stats(PROJECT_ID, ISSUE_IID)
    assert result.time_estimate == 0
    assert result.total_time_spent == 0


def test_my_issues(gitlab_token):
    """Smoke test: my_issues returns a list of IssueSummary objects."""
    pook.get(
        f"{BASE_URL}/issues",
        reply=200,
        response_json=load("issue_list.json"),
    )
    result = my_issues()
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "iid")
    assert hasattr(result[0], "title")
