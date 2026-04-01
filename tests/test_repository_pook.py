"""Pook-based HTTP integration tests for repository tools."""

import json
import pook
from pathlib import Path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.repository import (
    compare_branches,
    get_file_contents,
    list_directory,
    get_repository_tree,
    list_commits,
    get_commit,
    get_commit_diff,
    get_branch_diffs,
    get_blame,
    get_contributors,
    search_repositories,
)


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


COMMIT_SHA = "3aa0a9d772697316968905c014c00ad94bee9f33"
FILE_PATH = "README.md"


def test_get_file_contents():
    """Smoke test: get_file_contents decodes and returns file content."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/files/{FILE_PATH}",
        reply=200,
        response_json=load("file_contents.json"),
    )
    result = get_file_contents(PROJECT_ID, FILE_PATH)
    assert result.path == FILE_PATH
    assert isinstance(result.content, str)
    assert result.size > 0
    assert result.last_commit


def test_list_directory():
    """Smoke test: list_directory returns a list of FileSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/tree",
        reply=200,
        response_json=load("repository_tree.json"),
    )
    result = list_directory(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "name")
    assert hasattr(result[0], "type")


def test_get_repository_tree():
    """Smoke test: get_repository_tree returns FileSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/tree",
        reply=200,
        response_json=load("repository_tree.json"),
    )
    result = get_repository_tree(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "path")


def test_list_commits():
    """Smoke test: list_commits returns a list of CommitSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/commits",
        reply=200,
        response_json=load("commits_list.json"),
    )
    result = list_commits(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "sha")
    assert hasattr(result[0], "message")


def test_get_commit():
    """Smoke test: get_commit returns CommitDetails for the given SHA."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/commits/{COMMIT_SHA}",
        reply=200,
        response_json=load("commit_single.json"),
    )
    result = get_commit(PROJECT_ID, COMMIT_SHA)
    assert result.full_sha == COMMIT_SHA
    assert hasattr(result, "message")
    assert hasattr(result, "author")


def test_get_commit_diff():
    """Smoke test: get_commit_diff returns a CommitDiffResult with file changes."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/commits/{COMMIT_SHA}/diff",
        reply=200,
        response_json=load("commit_diff.json"),
    )
    result = get_commit_diff(PROJECT_ID, COMMIT_SHA)
    assert hasattr(result, "files_changed")
    assert isinstance(result.files_changed, list)
    assert result.total_files > 0


def test_get_branch_diffs():
    """Smoke test: get_branch_diffs returns a BranchDiffResult with file changes."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/compare",
        reply=200,
        response_json=load("branch_comparison.json"),
    )
    result = get_branch_diffs(PROJECT_ID, "master", "feature")
    assert result.from_ref == "master"
    assert result.to_ref == "feature"
    assert isinstance(result.files_changed, list)


def test_get_blame():
    """Smoke test: get_blame returns a list of blame entries."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/files/{FILE_PATH}/blame",
        reply=200,
        response_json=load("blame.json"),
    )
    result = get_blame(PROJECT_ID, FILE_PATH)
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "commit" in first
    assert "lines" in first


def test_get_contributors():
    """Smoke test: get_contributors returns a list of contributor dicts."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/repository/contributors",
        reply=200,
        response_json=load("contributors.json"),
    )
    result = get_contributors(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "name" in first
    assert "commits" in first


def test_search_repositories(gitlab_token):
    """Smoke test: search_repositories returns a list of project dicts."""
    pook.get(
        f"{BASE_URL}/projects",
        reply=200,
        response_json=load("project_list.json"),
    )
    result = search_repositories("gitlab")
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "id" in first
    assert "name" in first
