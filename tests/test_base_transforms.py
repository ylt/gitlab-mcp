"""Pure unit tests for gitlab_mcp.models.base utility functions."""

from datetime import datetime, timedelta, timezone

import pytest

from gitlab_mcp.models.base import (
    clean_note_body,
    clean_note_body_raw,
    format_timestamp_with_relative,
    relative_time,
    safe_str,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ago(**kwargs) -> datetime:
    return _now() - timedelta(**kwargs)


def _ahead(**kwargs) -> datetime:
    return _now() + timedelta(**kwargs)


# ---------------------------------------------------------------------------
# relative_time
# ---------------------------------------------------------------------------

class TestRelativeTime:
    def test_none_returns_unknown(self):
        assert relative_time(None) == "unknown"

    def test_future_datetime(self):
        assert relative_time(_ahead(seconds=60)) == "in the future"

    def test_30_seconds_ago_is_just_now(self):
        assert relative_time(_ago(seconds=30)) == "just now"

    def test_1_minute_ago_singular(self):
        result = relative_time(_ago(seconds=65))
        assert result == "1 minute ago"

    def test_5_minutes_ago(self):
        result = relative_time(_ago(minutes=5, seconds=5))
        assert "5 minutes ago" in result

    def test_1_hour_ago_singular(self):
        result = relative_time(_ago(hours=1, minutes=1))
        assert result == "1 hour ago"

    def test_3_hours_ago(self):
        result = relative_time(_ago(hours=3, minutes=5))
        assert "3 hours ago" in result

    def test_1_day_ago_singular(self):
        result = relative_time(_ago(days=1, hours=1))
        assert result == "1 day ago"

    def test_3_days_ago(self):
        result = relative_time(_ago(days=3, hours=1))
        assert "3 days ago" in result

    def test_1_week_ago_singular(self):
        result = relative_time(_ago(weeks=1, days=1))
        assert result == "1 week ago"

    def test_3_weeks_ago(self):
        result = relative_time(_ago(weeks=3, days=1))
        assert "3 weeks ago" in result

    def test_2_months_ago(self):
        # 2 months = ~60 days, use 62 to be safe
        result = relative_time(_ago(days=62))
        assert "2 months ago" in result

    def test_iso_string_input(self):
        iso = (_ago(hours=2)).isoformat().replace("+00:00", "Z")
        result = relative_time(iso)
        assert "hours ago" in result or "hour ago" in result

    def test_naive_datetime_treated_as_utc_no_raise(self):
        naive = datetime.utcnow() - timedelta(minutes=10)
        assert naive.tzinfo is None
        result = relative_time(naive)
        assert "minute" in result or "just now" in result


# ---------------------------------------------------------------------------
# format_timestamp_with_relative
# ---------------------------------------------------------------------------

class TestFormatTimestampWithRelative:
    def test_none_returns_unknown(self):
        assert format_timestamp_with_relative(None) == "unknown"

    def test_datetime_input_contains_ago_and_paren(self):
        dt = _ago(hours=1, minutes=5)
        result = format_timestamp_with_relative(dt)
        assert "ago" in result
        assert "(" in result and ")" in result

    def test_iso_string_input_contains_ago_and_paren(self):
        iso = (_ago(minutes=30)).isoformat()
        result = format_timestamp_with_relative(iso)
        assert "ago" in result or "just now" in result
        assert "(" in result


# ---------------------------------------------------------------------------
# clean_note_body
# ---------------------------------------------------------------------------

class TestCleanNoteBody:
    def test_none_returns_empty_string(self):
        assert clean_note_body(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert clean_note_body("") == ""

    def test_html_comment_stripped(self):
        result = clean_note_body("hello <!-- comment --> world")
        assert "<!--" not in result
        assert "hello" in result
        assert "world" in result

    def test_details_with_summary_becomes_collapsed_marker(self):
        text = "<details><summary>Title</summary>body content</details>"
        result = clean_note_body(text)
        assert "collapsed" in result
        assert "Title" in result

    def test_details_without_summary_becomes_collapsed_marker(self):
        text = "<details>no-summary content here</details>"
        result = clean_note_body(text)
        assert "collapsed" in result

    def test_3_plus_newlines_collapsed_to_2(self):
        text = "line1\n\n\n\nline2"
        result = clean_note_body(text)
        assert "\n\n\n" not in result
        assert "line1" in result
        assert "line2" in result

    def test_mixed_transforms_all_applied(self):
        text = (
            "start <!-- hidden --> middle\n\n\n\n"
            "<details><summary>Sec</summary>details body</details>\nend"
        )
        result = clean_note_body(text)
        assert "hidden" not in result
        assert "\n\n\n" not in result
        assert "collapsed" in result
        assert "Sec" in result
        assert "end" in result


# ---------------------------------------------------------------------------
# clean_note_body_raw
# ---------------------------------------------------------------------------

class TestCleanNoteBodyRaw:
    def test_none_returns_empty_string(self):
        assert clean_note_body_raw(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert clean_note_body_raw("") == ""

    def test_short_html_comment_preserved(self):
        short_comment = "<!-- short -->"
        text = f"hello {short_comment} world"
        result = clean_note_body_raw(text)
        assert short_comment in result

    def test_long_html_comment_stripped(self):
        long_content = "x" * 210
        long_comment = f"<!-- {long_content} -->"
        assert len(long_comment) > 200
        text = f"before {long_comment} after"
        result = clean_note_body_raw(text)
        assert long_comment not in result
        assert "before" in result
        assert "after" in result

    def test_3_plus_newlines_collapsed_to_2(self):
        text = "a\n\n\n\nb"
        result = clean_note_body_raw(text)
        assert "\n\n\n" not in result
        assert "a" in result
        assert "b" in result


# ---------------------------------------------------------------------------
# safe_str
# ---------------------------------------------------------------------------

class TestSafeStr:
    def test_none_returns_empty_string(self):
        assert safe_str(None) == ""

    def test_non_empty_string_unchanged(self):
        assert safe_str("hello") == "hello"

    def test_whitespace_string_unchanged(self):
        # safe_str uses `or ""` — non-empty whitespace is truthy, preserved
        assert safe_str("  ") == "  "
