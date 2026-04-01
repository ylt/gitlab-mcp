"""Pook-based HTTP integration tests for user tools."""

import json
import pook
from pathlib import Path

from gitlab_mcp.tools.users import get_users, list_events

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BASE_URL = "https://gitlab.com/api/v4"


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


def test_get_users(gitlab_token):
    pook.get(
        f"{BASE_URL}/users",
        reply=200,
        response_json=load("users_list.json"),
    )
    result = get_users()
    assert isinstance(result, list)
    assert len(result) > 0
    assert hasattr(result[0], "id")
    assert hasattr(result[0], "username")


def test_list_events(gitlab_token):
    pook.get(
        f"{BASE_URL}/events",
        reply=200,
        response_json=load("events_list.json"),
    )
    result = list_events()
    assert isinstance(result, list)
    assert len(result) > 0
