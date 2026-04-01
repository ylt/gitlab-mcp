"""Pook-based HTTP integration tests for issue tools."""

import json
import pook
from pathlib import Path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.issues import list_issues, get_issue

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
