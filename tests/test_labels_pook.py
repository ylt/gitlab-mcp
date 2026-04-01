"""Pook-based HTTP integration tests for label tools."""

import json
import pook
from pathlib import Path

from gitlab_mcp.tools.labels import list_labels, get_label

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
LABEL_ID = 16558712
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


def _mock_project():
    pook.get(f"{BASE_URL}/projects/{PROJECT_ID}", reply=200, response_json=load("project.json"))


def test_list_labels(mock_project):
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/labels",
        reply=200,
        response_json=load("labels_list.json"),
    )
    result = list_labels(PROJECT_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "name")
    assert hasattr(result[0], "color")


def test_get_label(mock_project):
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/labels/{LABEL_ID}",
        reply=200,
        response_json=load("label_single.json"),
    )
    result = get_label(PROJECT_ID, LABEL_ID)
    assert result.id == LABEL_ID
    assert result.name
