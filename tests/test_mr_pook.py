"""Pook-based HTTP integration tests for merge request tools."""

import json
import pook
from pathlib import Path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
MR_IID = 229854
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.merge_requests import (
    get_merge_request,
    list_merge_requests,
    get_merge_request_diff,
    list_merge_request_diffs,
    get_merge_request_diffs,
    list_merge_request_versions,
)


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def _mock_mr_approvals():
    """Mock the approvals endpoint called by MergeRequestSummary.from_gitlab."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/approvals",
        reply=200,
        response_json={"approvals_required": 0, "approvals_left": 0, "approved_by": []},
    )


def _mock_mr_single():
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}",
        reply=200,
        response_json=load("mr_single.json"),
    )


def _mock_mr_list():
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests",
        reply=200,
        response_json=load("mr_list.json"),
    )
    # list returns 2 MRs; approvals are fetched for each
    for iid in [mr["iid"] for mr in load("mr_list.json")]:
        pook.get(
            f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{iid}/approvals",
            reply=200,
            response_json={"approvals_required": 0, "approvals_left": 0, "approved_by": []},
        )


def _mock_mr_changes():
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/changes",
        reply=200,
        response_json=load("mr_changes.json"),
    )


def _mock_mr_versions():
    """Mock the versions endpoint (python-gitlab uses /versions not /diffs)."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/versions",
        reply=200,
        response_json=load("mr_versions_list.json"),
    )


# --- Basic smoke tests ---

def test_get_merge_request():
    _mock_project()
    _mock_mr_single()
    _mock_mr_approvals()
    result = get_merge_request(PROJECT_ID, MR_IID)
    assert result.iid == MR_IID
    assert result.title == "[OpenAPI3] Remove legacy spec"
    assert result.state in ("opened", "closed", "merged", "locked")
    assert result.source_branch
    assert result.target_branch


def test_list_merge_requests():
    _mock_project()
    _mock_mr_list()
    results = list_merge_requests(PROJECT_ID)
    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0].iid == MR_IID


# --- Critical regression tests: diffs should return file changes, not version metadata ---

def test_get_merge_request_diff_returns_file_paths():
    """Regression: get_merge_request_diff must return file paths, not version metadata."""
    _mock_project()
    _mock_mr_single()
    _mock_mr_changes()
    results = get_merge_request_diff(PROJECT_ID, MR_IID)
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    # Must have a path field with a real file path
    assert hasattr(first, "path")
    assert isinstance(first.path, str)
    assert len(first.path) > 0
    # Must NOT have version fields
    assert not hasattr(first, "head_commit_sha")
    assert not hasattr(first, "base_commit_sha")


def test_list_merge_request_diffs_returns_file_paths():
    """Regression: list_merge_request_diffs must return file paths, not version metadata."""
    _mock_project()
    _mock_mr_single()
    _mock_mr_changes()
    results = list_merge_request_diffs(PROJECT_ID, MR_IID)
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert hasattr(first, "path")
    assert isinstance(first.path, str)
    assert len(first.path) > 0
    # Must NOT have version fields
    assert not hasattr(first, "head_commit_sha")
    assert not hasattr(first, "base_commit_sha")


def test_get_merge_request_diffs_returns_file_paths():
    """Regression: get_merge_request_diffs must return file paths, not version metadata."""
    _mock_project()
    _mock_mr_single()
    _mock_mr_changes()
    results = get_merge_request_diffs(PROJECT_ID, MR_IID)
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert hasattr(first, "path")
    assert isinstance(first.path, str)
    assert len(first.path) > 0
    # Must NOT have version fields
    assert not hasattr(first, "head_commit_sha")
    assert not hasattr(first, "base_commit_sha")


def test_get_merge_request_diff_first_path_matches_fixture():
    """Verify the actual file path from the fixture is returned."""
    _mock_project()
    _mock_mr_single()
    _mock_mr_changes()
    results = get_merge_request_diff(PROJECT_ID, MR_IID)
    # The fixture has doc/api/openapi/openapi.yaml as first entry
    assert results[0].path == "doc/api/openapi/openapi.yaml"


# --- MR version tests ---

def test_list_merge_request_versions():
    """Smoke test: list_merge_request_versions returns version objects."""
    _mock_project()
    _mock_mr_single()
    _mock_mr_versions()
    results = list_merge_request_versions(PROJECT_ID, MR_IID)
    assert isinstance(results, list)
    assert len(results) == 1
    version = results[0]
    assert hasattr(version, "id")
    assert hasattr(version, "head_commit_sha")
    assert hasattr(version, "base_commit_sha")
    assert hasattr(version, "start_commit_sha")


def test_mr_version_missing_updated_at_is_ok():
    """Regression: MergeRequestVersion must not fail when updated_at is absent."""
    # The mr_versions_list.json fixture has no updated_at field — intentional
    fixture = load("mr_versions_list.json")
    assert isinstance(fixture, list)
    # Confirm fixture has no updated_at
    assert "updated_at" not in fixture[0]

    _mock_project()
    _mock_mr_single()
    _mock_mr_versions()
    # Should parse without raising ValidationError
    results = list_merge_request_versions(PROJECT_ID, MR_IID)
    assert len(results) == 1
    assert results[0].updated_at is None
