"""Pook-based HTTP integration tests for discussion tools."""

import json
import pook
from pathlib import Path

from gitlab_mcp.tools.discussions import list_issue_discussions, get_mr_discussion, mr_discussions

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"
ISSUE_IID = 595528
MR_IID = 229854
MR_DISCUSSION_ID = "c7b8e5ca640638057f1df63c0c224db559419800"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def test_list_issue_discussions():
    """Smoke test: list_issue_discussions returns a list of DiscussionSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}",
        reply=200,
        response_json=load("issue_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/issues/{ISSUE_IID}/discussions",
        reply=200,
        response_json=load("issue_discussions.json"),
    )
    result = list_issue_discussions(PROJECT_ID, ISSUE_IID, include_system=True)
    assert isinstance(result, list)
    assert len(result) > 0


def test_get_mr_discussion():
    """Smoke test: get_mr_discussion returns a DiscussionDetail with the correct id."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}",
        reply=200,
        response_json=load("mr_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/discussions/{MR_DISCUSSION_ID}",
        reply=200,
        response_json=load("mr_discussion_single.json"),
    )
    result = get_mr_discussion(PROJECT_ID, MR_IID, MR_DISCUSSION_ID)
    assert result.id == MR_DISCUSSION_ID
    assert hasattr(result, "notes")
    assert isinstance(result.notes, list)


def test_mr_discussions():
    """Smoke test: mr_discussions returns a list of DiscussionSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}",
        reply=200,
        response_json=load("mr_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/discussions",
        reply=200,
        response_json=load("mr_discussions.json"),
    )
    result = mr_discussions(PROJECT_ID, MR_IID)
    assert isinstance(result, list)
    assert len(result) > 0
