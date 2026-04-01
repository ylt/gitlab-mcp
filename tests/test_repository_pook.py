"""Pook-based HTTP integration tests for repository tools."""

import json
import pook
from pathlib import Path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.repository import compare_branches


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def _mock_compare(source: str = "master", target: str = "feature"):
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/compare",
        reply=200,
        response_json=load("branch_comparison.json"),
    )


def test_compare_branches_returns_commits():
    """Smoke test: compare_branches returns a list of commits."""
    _mock_project()
    _mock_compare()
    result = compare_branches(PROJECT_ID, "master", "feature")
    assert hasattr(result, "commits")
    assert isinstance(result.commits, list)
    assert len(result.commits) > 0


def test_compare_branches_author_is_string():
    """Regression: commit author must be a plain string, not a UserRef or object."""
    _mock_project()
    _mock_compare()
    result = compare_branches(PROJECT_ID, "master", "feature")
    for commit in result.commits:
        assert hasattr(commit, "author")
        assert isinstance(commit.author, str), (
            f"Expected author to be str, got {type(commit.author)}: {commit.author!r}"
        )


def test_compare_branches_diffs_have_paths():
    """Regression: diff entries must have a path field with a real file path."""
    _mock_project()
    _mock_compare()
    result = compare_branches(PROJECT_ID, "master", "feature")
    assert hasattr(result, "diffs")
    assert isinstance(result.diffs, list)
    assert len(result.diffs) > 0
    for diff in result.diffs:
        assert hasattr(diff, "path")
        assert isinstance(diff.path, str)
        assert len(diff.path) > 0


def test_compare_branches_from_to_refs():
    """Verify from_ref and to_ref are set correctly in the result."""
    _mock_project()
    _mock_compare()
    result = compare_branches(PROJECT_ID, "master", "feature")
    assert result.from_ref == "master"
    assert result.to_ref == "feature"
