"""Pure unit tests for client-side discussion transform functions."""

import pytest
from datetime import datetime, timezone, timedelta

from gitlab_mcp.tools.discussions import _parse_newer_than, _truncate_note, _filter_discussions
from gitlab_mcp.models.discussions import NoteSummary, DiscussionSummary
from gitlab_mcp.models.merge_requests import MergeRequestDiff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_note(
    *,
    id: int = 1,
    body: str = "hello",
    author: str = "alice",
    created_at: str = "2026-03-18T10:00:00Z",
    system: bool = False,
    resolvable: bool | None = False,
    resolved: bool | None = False,
) -> NoteSummary:
    """Build a NoteSummary via model_construct (bypasses validators)."""
    return NoteSummary.model_construct(
        id=id,
        body=body,
        author=author,
        created_at=created_at,
        updated_at=None,
        system=system,
        resolvable=resolvable,
        resolved=resolved,
    )


def make_discussion(
    notes: list[NoteSummary],
    *,
    id: str = "abc123",
    state: str = "comment",
    note_count: int | None = None,
    individual_note: bool = False,
) -> DiscussionSummary:
    """Build a DiscussionSummary via model_construct."""
    return DiscussionSummary.model_construct(
        id=id,
        state=state,
        note_count=note_count if note_count is not None else len(notes),
        notes=notes,
        individual_note=individual_note,
    )


# ---------------------------------------------------------------------------
# _parse_newer_than
# ---------------------------------------------------------------------------

class TestParseNewerThan:
    def _approx_ago(self, result: datetime, seconds: float, tolerance: float = 5.0) -> None:
        """Assert result is approximately `seconds` in the past."""
        now = datetime.now(timezone.utc)
        delta = (now - result).total_seconds()
        assert abs(delta - seconds) <= tolerance, (
            f"Expected ~{seconds}s ago, got {delta}s ago"
        )

    def test_1h(self):
        result = _parse_newer_than("1h")
        self._approx_ago(result, 3600)

    def test_2d(self):
        result = _parse_newer_than("2d")
        self._approx_ago(result, 2 * 86400)

    def test_30m(self):
        result = _parse_newer_than("30m")
        self._approx_ago(result, 30 * 60)

    def test_1w(self):
        result = _parse_newer_than("1w")
        self._approx_ago(result, 604800)

    def test_iso_fixed_datetime(self):
        result = _parse_newer_than("2026-03-16T00:00:00Z")
        expected = datetime(2026, 3, 16, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            _parse_newer_than("invalid")

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError):
            _parse_newer_than("99x")


# ---------------------------------------------------------------------------
# _truncate_note
# ---------------------------------------------------------------------------

class TestTruncateNote:
    def test_short_body_unchanged(self):
        note = make_note(body="short text")
        result = _truncate_note(note)
        assert result.body == "short text"

    def test_body_at_boundary_unchanged(self):
        body = "x" * 500
        note = make_note(body=body)
        result = _truncate_note(note)
        assert result.body == body

    def test_body_over_limit_truncated(self):
        body = "x" * 501
        note = make_note(body=body)
        result = _truncate_note(note)
        assert result.body is not None
        assert result.body.startswith("x" * 500)
        assert "[... truncated" in result.body

    def test_truncated_body_starts_with_500_original_chars(self):
        body = "a" * 600
        note = make_note(body=body)
        result = _truncate_note(note)
        assert result.body is not None
        assert result.body[:500] == "a" * 500
        assert result.body[500:].startswith("\n\n[... truncated")

    def test_returns_same_note_object(self):
        note = make_note(body="hi")
        result = _truncate_note(note)
        assert result is note


# ---------------------------------------------------------------------------
# _filter_discussions
# ---------------------------------------------------------------------------

class TestFilterDiscussions:

    # -- system note filtering --

    def test_system_notes_excluded_by_default(self):
        sys_note = make_note(id=1, body="assigned to alice", system=True)
        disc = make_discussion([sys_note])
        result = _filter_discussions([disc], include_system=False)
        assert result == []

    def test_system_notes_included_when_flag_true(self):
        sys_note = make_note(id=1, body="assigned to alice", system=True)
        disc = make_discussion([sys_note])
        result = _filter_discussions([disc], include_system=True)
        assert len(result) == 1

    def test_discussion_dropped_if_all_notes_are_system(self):
        sys_note = make_note(id=1, system=True)
        disc = make_discussion([sys_note])
        result = _filter_discussions([disc], include_system=False)
        assert result == []

    # -- newer_than filtering --

    def _old_iso(self) -> str:
        """ISO string 30 days in the past."""
        dt = datetime.now(timezone.utc) - timedelta(days=30)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _recent_iso(self) -> str:
        """ISO string 1 minute in the past."""
        dt = datetime.now(timezone.utc) - timedelta(minutes=1)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_newer_than_drops_old_discussion(self):
        old_note = make_note(id=1, created_at=self._old_iso())
        disc = make_discussion([old_note])
        result = _filter_discussions([disc], include_system=False, newer_than="1h")
        assert result == []

    def test_newer_than_keeps_recent_discussion(self):
        recent_note = make_note(id=1, created_at=self._recent_iso())
        disc = make_discussion([recent_note])
        result = _filter_discussions([disc], include_system=False, newer_than="1h")
        assert len(result) == 1

    def test_newer_than_keeps_discussion_with_any_recent_note(self):
        old_note = make_note(id=1, created_at=self._old_iso())
        recent_note = make_note(id=2, created_at=self._recent_iso())
        disc = make_discussion([old_note, recent_note])
        result = _filter_discussions([disc], include_system=False, newer_than="1h")
        assert len(result) == 1

    # -- state computation --

    def test_state_comment_when_no_resolvable_notes(self):
        note = make_note(resolvable=False)
        disc = make_discussion([note])
        result = _filter_discussions([disc], include_system=False)
        assert result[0].state == "comment"

    def test_state_unresolved_when_some_unresolved(self):
        note = make_note(resolvable=True, resolved=False)
        disc = make_discussion([note])
        result = _filter_discussions([disc], include_system=False)
        assert result[0].state == "unresolved"

    def test_state_resolved_when_all_resolvable_resolved(self):
        note = make_note(resolvable=True, resolved=True)
        disc = make_discussion([note])
        result = _filter_discussions([disc], include_system=False)
        assert result[0].state == "resolved"

    # -- resolved collapse --

    def test_resolved_discussion_notes_collapsed_to_empty(self):
        note = make_note(resolvable=True, resolved=True)
        disc = make_discussion([note])
        result = _filter_discussions([disc], include_system=False)
        assert result[0].notes == []

    # -- note collapsing by thread length --

    def test_single_note_thread_has_one_note(self):
        note = make_note(id=1, resolvable=True, resolved=False)
        disc = make_discussion([note])
        result = _filter_discussions([disc], include_system=False)
        assert len(result[0].notes) == 1

    def test_two_note_thread_has_placeholder_between(self):
        # Production code: len(notes) != 1 → else branch → [first, placeholder, last]
        # skipped = len(notes) - 2 = 0, placeholder always inserted
        note1 = make_note(id=1, resolvable=True, resolved=False)
        note2 = make_note(id=2, resolvable=True, resolved=False)
        disc = make_discussion([note1, note2])
        result = _filter_discussions([disc], include_system=False)
        assert len(result[0].notes) == 3

    def test_three_note_thread_has_placeholder_in_middle(self):
        note1 = make_note(id=1, resolvable=True, resolved=False)
        note2 = make_note(id=2, resolvable=True, resolved=False)
        note3 = make_note(id=3, resolvable=True, resolved=False)
        disc = make_discussion([note1, note2, note3])
        result = _filter_discussions([disc], include_system=False)
        notes = result[0].notes
        assert len(notes) == 3
        assert notes[0].id == 1
        assert notes[2].id == 3
        # Middle note is the placeholder
        assert "skipped" in (notes[1].body or "")

    # -- include_all_notes --

    def test_include_all_notes_preserves_all(self):
        notes = [make_note(id=i, resolvable=True, resolved=False) for i in range(1, 6)]
        disc = make_discussion(notes)
        result = _filter_discussions([disc], include_system=False, include_all_notes=True)
        assert len(result[0].notes) == 5

    # -- note_count --

    def test_note_count_set_to_total_before_collapsing(self):
        notes = [make_note(id=i, resolvable=True, resolved=False) for i in range(1, 6)]
        disc = make_discussion(notes)
        result = _filter_discussions([disc], include_system=False)
        assert result[0].note_count == 5


# ---------------------------------------------------------------------------
# NoteSummary.flatten_author
# ---------------------------------------------------------------------------

class TestNoteSummaryFlattenAuthor:

    def test_nested_author_dict_extracted(self):
        note = NoteSummary.model_validate({
            "id": 1,
            "body": "hello",
            "author": {"username": "foo", "id": 42},
            "created_at": "2026-03-18T10:00:00Z",
        })
        assert note.author == "foo"

    def test_author_already_string_passes_through(self):
        note = NoteSummary.model_validate({
            "id": 1,
            "body": "hello",
            "author": "bob",
            "created_at": "2026-03-18T10:00:00Z",
        })
        assert note.author == "bob"

    def test_author_dict_missing_username_falls_back_to_unknown(self):
        note = NoteSummary.model_validate({
            "id": 1,
            "body": "hello",
            "author": {"id": 99},
            "created_at": "2026-03-18T10:00:00Z",
        })
        assert note.author == "unknown"


# ---------------------------------------------------------------------------
# MergeRequestDiff.status computed field
# ---------------------------------------------------------------------------

class TestMergeRequestDiffStatus:

    def test_new_file_is_added(self):
        diff = MergeRequestDiff.model_validate({
            "new_path": "src/foo.py",
            "new_file": True,
            "deleted_file": False,
            "renamed_file": False,
            "diff": "",
        })
        assert diff.status == "added"

    def test_deleted_file_is_deleted(self):
        diff = MergeRequestDiff.model_validate({
            "new_path": "src/foo.py",
            "new_file": False,
            "deleted_file": True,
            "renamed_file": False,
            "diff": "",
        })
        assert diff.status == "deleted"

    def test_renamed_file_is_renamed(self):
        diff = MergeRequestDiff.model_validate({
            "new_path": "src/bar.py",
            "old_path": "src/foo.py",
            "new_file": False,
            "deleted_file": False,
            "renamed_file": True,
            "diff": "",
        })
        assert diff.status == "renamed"

    def test_no_flags_is_modified(self):
        diff = MergeRequestDiff.model_validate({
            "new_path": "src/foo.py",
            "new_file": False,
            "deleted_file": False,
            "renamed_file": False,
            "diff": "@@ -1 +1 @@\n-old\n+new",
        })
        assert diff.status == "modified"
