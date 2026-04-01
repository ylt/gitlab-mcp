"""Pook-based HTTP integration tests for pipeline tools."""

import json
import pook
from pathlib import Path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.pipelines import (
    list_pipelines,
    get_pipeline,
    list_pipeline_jobs,
    get_pipeline_job,
    get_job_log,
    list_pipeline_trigger_jobs,
)

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


JOB_ID = 13747907013


def test_list_pipeline_jobs():
    """Smoke test: list_pipeline_jobs returns a list of JobSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/pipelines/{PIPELINE_ID}",
        reply=200,
        response_json=load("pipeline_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/pipelines/{PIPELINE_ID}/jobs",
        reply=200,
        response_json=load("pipeline_jobs.json"),
    )
    results = list_pipeline_jobs(PROJECT_ID, PIPELINE_ID)
    assert isinstance(results, list)
    assert len(results) > 0
    assert hasattr(results[0], "id")
    assert hasattr(results[0], "status")
    assert hasattr(results[0], "name")


def test_get_pipeline_job():
    """Smoke test: get_pipeline_job returns a JobSummary for the given job id."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/jobs/{JOB_ID}",
        reply=200,
        response_json=load("pipeline_job_single.json"),
    )
    result = get_pipeline_job(PROJECT_ID, JOB_ID)
    assert result.id == JOB_ID
    assert hasattr(result, "status")
    assert hasattr(result, "name")


def test_get_job_log():
    """Smoke test: get_job_log returns a JobLogResult with log content."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/jobs/{JOB_ID}",
        reply=200,
        response_json=load("pipeline_job_single.json"),
    )
    (
        pook.get(f"{BASE_URL}/projects/{PROJECT_ID}/jobs/{JOB_ID}/trace")
        .reply(200)
        .body("Running pre-merge-checks\nStatus: passed\n")
    )
    result = get_job_log(PROJECT_ID, JOB_ID)
    assert result.job_id == JOB_ID
    assert "passed" in result.log
    assert isinstance(result.truncated, bool)
    assert result.total_lines > 0


def test_list_pipeline_trigger_jobs():
    """Smoke test: list_pipeline_trigger_jobs returns a list of JobSummary objects."""
    _mock_project()
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/pipelines/{PIPELINE_ID}",
        reply=200,
        response_json=load("pipeline_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/pipelines/{PIPELINE_ID}/jobs",
        reply=200,
        response_json=load("pipeline_jobs.json"),
    )
    results = list_pipeline_trigger_jobs(PROJECT_ID, PIPELINE_ID)
    assert isinstance(results, list)
    assert len(results) > 0
    assert hasattr(results[0], "id")
