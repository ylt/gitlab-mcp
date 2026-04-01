"""Pook-based HTTP integration tests for milestone tools."""

import json
import pook
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"
MILESTONE_ID = 22878
MILESTONE_ISSUE_IID = 9  # iid of first issue in milestone_issues.json


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.milestones import (
    list_milestones,
    get_milestone,
    get_milestone_issues,
    get_milestone_merge_requests,
    get_milestone_burndown_events,
    get_milestone_issue,
)
from gitlab_mcp.models.milestones import MilestoneSummary
from gitlab_mcp.models.issues import IssueSummary


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def _mock_milestone():
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/milestones/{MILESTONE_ID}",
        reply=200,
        response_json=load("milestone_single.json"),
    )


def _mock_mr_approvals(iid: int):
    """Mock the approvals endpoint called by MergeRequestSummary.from_gitlab."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{iid}/approvals",
        reply=200,
        response_json={"approvals_required": 0, "approvals_left": 0, "approved_by": []},
    )


def test_list_milestones():
    """Smoke test: list_milestones returns a list of MilestoneSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/milestones",
        reply=200,
        response_json=load("milestones_list.json"),
    )
    results = list_milestones(PROJECT_ID)
    assert isinstance(results, list)
    assert len(results) > 0
    assert isinstance(results[0], MilestoneSummary)


def test_get_milestone():
    """Smoke test: get_milestone returns a MilestoneSummary with correct id and title."""
    _mock_project()
    _mock_milestone()
    result = get_milestone(PROJECT_ID, MILESTONE_ID)
    assert isinstance(result, MilestoneSummary)
    assert result.id == MILESTONE_ID
    assert result.title == "7.14"


def test_get_milestone_issues():
    """Smoke test: get_milestone_issues returns a list of IssueSummary objects."""
    _mock_project()
    _mock_milestone()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/milestones/{MILESTONE_ID}/issues",
        reply=200,
        response_json=load("milestone_issues.json"),
    )
    results = get_milestone_issues(PROJECT_ID, MILESTONE_ID)
    assert isinstance(results, list)
    assert len(results) > 0


def test_get_milestone_merge_requests():
    """Smoke test: get_milestone_merge_requests returns a list."""
    _mock_project()
    _mock_milestone()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/milestones/{MILESTONE_ID}/merge_requests",
        reply=200,
        response_json=load("milestone_merge_requests.json"),
    )
    # MergeRequestSummary.from_gitlab fetches approvals for each MR
    for iid in [mr["iid"] for mr in load("milestone_merge_requests.json")]:
        _mock_mr_approvals(iid)
    results = get_milestone_merge_requests(PROJECT_ID, MILESTONE_ID)
    assert isinstance(results, list)
    assert len(results) > 0


def test_get_milestone_burndown_events():
    """Smoke test: get_milestone_burndown_events returns a list."""
    _mock_project()
    _mock_milestone()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/milestones/{MILESTONE_ID}/burndown_events",
        reply=200,
        response_json=load("milestone_burndown_events.json"),
    )
    results = get_milestone_burndown_events(PROJECT_ID, MILESTONE_ID)
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert first.id == 1
    assert first.issue_id == 12345


def test_get_milestone_issue():
    """Smoke test: get_milestone_issue returns an IssueSummary for the given iid.

    get_milestone_issue lists all milestone issues and filters by iid.
    """
    _mock_project()
    _mock_milestone()
    # Tool calls milestone.issues() which hits the list endpoint
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/milestones/{MILESTONE_ID}/issues",
        reply=200,
        response_json=load("milestone_issues.json"),
    )
    result = get_milestone_issue(PROJECT_ID, MILESTONE_ID, MILESTONE_ISSUE_IID)
    assert isinstance(result, IssueSummary)
    assert result.iid == MILESTONE_ISSUE_IID
