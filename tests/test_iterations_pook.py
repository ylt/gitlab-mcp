"""Pook-based HTTP integration tests for iteration tools."""

import json
import pook
from pathlib import Path

from gitlab_mcp.tools.iterations import list_group_iterations

FIXTURES_DIR = Path(__file__).parent / "fixtures"
GROUP_ID = "9970"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


def test_list_group_iterations(gitlab_token):
    pook.get(
        f"{BASE_URL}/groups/{GROUP_ID}",
        reply=200,
        response_json=load("group_single.json"),
    )
    pook.get(
        f"{BASE_URL}/groups/{GROUP_ID}/iterations",
        reply=200,
        response_json=load("group_iterations.json"),
    )
    result = list_group_iterations(GROUP_ID)
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "id")
    assert hasattr(result[0], "title")
