"""Pook-based HTTP integration tests for pipeline tools."""

import json
import pook
from pathlib import Path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.pipelines import list_pipelines, get_pipeline

PIPELINE_ID = 2424049310  # from pipeline_single.json


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def test_list_pipelines():
    """Smoke test: list_pipelines returns a list of pipeline summaries."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/pipelines",
        reply=200,
        response_json=load("pipeline_list.json"),
    )
    results = list_pipelines(PROJECT_ID)
    assert isinstance(results, list)
    assert len(results) == 3
    first = results[0]
    assert hasattr(first, "id")
    assert hasattr(first, "status")
    assert hasattr(first, "ref")
    assert first.id == PIPELINE_ID


def test_get_pipeline():
    """Smoke test: get_pipeline returns a single pipeline summary."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/pipelines/{PIPELINE_ID}",
        reply=200,
        response_json=load("pipeline_single.json"),
    )
    result = get_pipeline(PROJECT_ID, PIPELINE_ID)
    assert result.id == PIPELINE_ID
    assert hasattr(result, "status")
    assert hasattr(result, "ref")
    assert hasattr(result, "sha")
