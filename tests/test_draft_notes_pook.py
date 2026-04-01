"""Pook-based HTTP integration tests for draft note tools."""

import json
import pook
from pathlib import Path

from gitlab_mcp.tools.draft_notes import list_draft_notes, get_draft_note

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ID = "278964"
BASE_URL = "https://gitlab.com/api/v4"
MR_IID = 229854
DRAFT_NOTE_ID = 1


def load(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


def test_list_draft_notes(mock_project):
    """Smoke test: list_draft_notes returns a list of DraftNoteSummary objects."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}",
        reply=200,
        response_json=load("mr_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/draft_notes",
        reply=200,
        response_json=load("draft_notes_list.json"),
    )
    result = list_draft_notes(PROJECT_ID, MR_IID)
    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert first.id == DRAFT_NOTE_ID
    assert hasattr(first, "body")


def test_get_draft_note(mock_project):
    """Smoke test: get_draft_note returns a single DraftNoteSummary."""
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}",
        reply=200,
        response_json=load("mr_single.json"),
    )
    pook.get(
        f"{BASE_URL}/projects/{PROJECT_ID}/merge_requests/{MR_IID}/draft_notes/{DRAFT_NOTE_ID}",
        reply=200,
        response_json=load("draft_note_single.json"),
    )
    result = get_draft_note(PROJECT_ID, MR_IID, DRAFT_NOTE_ID)
    assert result.id == DRAFT_NOTE_ID
    assert hasattr(result, "body")
