"""Pook-based HTTP integration tests for namespace tools."""

import json
import pook
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BASE_URL = "https://gitlab.com/api/v4"

NAMESPACE_ID = 58160  # from namespace_single.json


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


from gitlab_mcp.tools.namespaces import list_namespaces, get_namespace, verify_namespace


def test_list_namespaces(gitlab_token):
    """Smoke test: list_namespaces returns a list of namespace summaries."""
    pook.get(
        f"{BASE_URL}/namespaces",
        reply=200,
        response_json=load("namespaces_list.json"),
    )
    result = list_namespaces()
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert hasattr(first, "id")
    assert hasattr(first, "name")


def test_get_namespace(gitlab_token):
    """Smoke test: get_namespace returns a single namespace summary."""
    pook.get(
        f"{BASE_URL}/namespaces/{NAMESPACE_ID}",
        reply=200,
        response_json=load("namespace_single.json"),
    )
    result = get_namespace(NAMESPACE_ID)
    assert result.id == NAMESPACE_ID
    assert hasattr(result, "name")
    assert hasattr(result, "kind")


def test_verify_namespace_not_found(gitlab_token):
    """Smoke test: verify_namespace returns exists=False for a namespace that doesn't exist."""
    # pook is on with no mock for this path → _get_namespace_info catches the exception → None
    result = verify_namespace("nonexistent-namespace-xyz-abc")
    assert result.exists is False
    assert result.error is not None
    assert "nonexistent-namespace-xyz-abc" in result.error
