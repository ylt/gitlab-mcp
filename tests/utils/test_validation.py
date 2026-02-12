"""Tests for validation utilities."""

from datetime import datetime

import pytest

from gitlab_mcp.utils.validation import (
    ValidationError,
    validate_color,
    validate_date,
    validate_format,
    validate_non_negative_int,
    validate_positive_int,
    validate_scope,
    validate_state,
    validate_string_length,
)


class TestValidateColor:
    """Tests for validate_color."""

    def test_valid_color_with_hash(self):
        """Should accept valid color with # prefix."""
        assert validate_color("#FF0000") == "FF0000"

    def test_valid_color_without_hash(self):
        """Should accept valid color without # prefix."""
        assert validate_color("FF0000") == "FF0000"

    def test_lowercase_color(self):
        """Should normalize to uppercase."""
        assert validate_color("#ff0000") == "FF0000"
        assert validate_color("00ff00") == "00FF00"

    def test_mixed_case_color(self):
        """Should handle mixed case."""
        assert validate_color("#FfAaBb") == "FFAABB"

    def test_empty_color(self):
        """Should reject empty color."""
        with pytest.raises(ValidationError, match="empty"):
            validate_color("")

    def test_none_color(self):
        """Should reject None."""
        with pytest.raises(ValidationError):
            validate_color(None)  # type: ignore

    def test_invalid_hex_characters(self):
        """Should reject invalid hex characters."""
        with pytest.raises(ValidationError, match="Invalid color format"):
            validate_color("#GGGGGG")

    def test_too_short_color(self):
        """Should reject color that's too short."""
        with pytest.raises(ValidationError, match="Invalid color format"):
            validate_color("#FFF")

    def test_too_long_color(self):
        """Should reject color that's too long."""
        with pytest.raises(ValidationError, match="Invalid color format"):
            validate_color("#FF0000FF")

    def test_color_with_spaces(self):
        """Should reject color with spaces."""
        with pytest.raises(ValidationError, match="Invalid color format"):
            validate_color("# FF 00 00")

    def test_color_no_hex_characters(self):
        """Should reject strings without valid hex."""
        with pytest.raises(ValidationError, match="Invalid color format"):
            validate_color("ZZZZZZ")


class TestValidateDate:
    """Tests for validate_date."""

    def test_valid_date_string(self):
        """Should accept valid date string."""
        assert validate_date("2024-01-15") == "2024-01-15"

    def test_valid_date_datetime(self):
        """Should accept datetime object."""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        assert validate_date(dt) == "2024-01-15"

    def test_valid_date_leap_year(self):
        """Should accept leap year date."""
        assert validate_date("2024-02-29") == "2024-02-29"

    def test_empty_date_string(self):
        """Should reject empty date string."""
        with pytest.raises(ValidationError, match="empty"):
            validate_date("")

    def test_invalid_date_format(self):
        """Should reject invalid date format."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("01-15-2024")

    def test_invalid_date_format_slash(self):
        """Should reject date with slashes."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("01/15/2024")

    def test_invalid_date_format_dmy(self):
        """Should reject DD-MM-YYYY format."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("15-01-2024")

    def test_invalid_month(self):
        """Should reject invalid month."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("2024-13-01")

    def test_invalid_day(self):
        """Should reject invalid day."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("2024-02-30")

    def test_non_string_non_datetime(self):
        """Should reject non-string, non-datetime types."""
        with pytest.raises(ValidationError, match="must be string or datetime"):
            validate_date(12345)  # type: ignore

    def test_date_only_year_month(self):
        """Should reject incomplete date."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("2024-01")

    def test_date_with_time(self):
        """Should reject date with time component."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("2024-01-15 12:30:00")


class TestValidateFormat:
    """Tests for validate_format."""

    def test_valid_format(self):
        """Should accept valid value from list."""
        assert validate_format("active", ["active", "inactive"]) == "active"

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert validate_format("ACTIVE", ["active", "inactive"]) == "active"
        assert validate_format("Active", ["active", "inactive"]) == "active"

    def test_empty_value(self):
        """Should reject empty value."""
        with pytest.raises(ValidationError, match="empty"):
            validate_format("", ["active", "inactive"])

    def test_invalid_value(self):
        """Should reject value not in list."""
        with pytest.raises(ValidationError, match="Invalid"):
            validate_format("unknown", ["active", "inactive"])

    def test_custom_parameter_name(self):
        """Should include custom parameter name in error."""
        with pytest.raises(ValidationError, match="status"):
            validate_format("bad", ["good", "okay"], name="status")

    def test_single_option(self):
        """Should work with single option."""
        assert validate_format("only", ["only"]) == "only"

    def test_many_options(self):
        """Should work with many options."""
        allowed = ["a", "b", "c", "d", "e"]
        assert validate_format("c", allowed) == "c"

    def test_non_string_value(self):
        """Should reject non-string value."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_format(123, ["123"])  # type: ignore


class TestValidateState:
    """Tests for validate_state."""

    def test_valid_states(self):
        """Should accept valid MR/Issue states."""
        assert validate_state("opened") == "opened"
        assert validate_state("closed") == "closed"
        assert validate_state("merged") == "merged"
        assert validate_state("all") == "all"

    def test_case_insensitive_state(self):
        """Should be case-insensitive."""
        assert validate_state("OPENED") == "opened"
        assert validate_state("Closed") == "closed"
        assert validate_state("MERGED") == "merged"

    def test_invalid_state(self):
        """Should reject invalid state."""
        with pytest.raises(ValidationError, match="state"):
            validate_state("invalid")

    def test_empty_state(self):
        """Should reject empty state."""
        with pytest.raises(ValidationError, match="empty"):
            validate_state("")

    def test_state_with_spaces(self):
        """Should reject state with spaces."""
        with pytest.raises(ValidationError):
            validate_state(" opened ")


class TestValidateScope:
    """Tests for validate_scope."""

    def test_valid_scopes(self):
        """Should accept valid discussion scopes."""
        assert validate_scope("note") == "note"
        assert validate_scope("diff_note") == "diff_note"
        assert validate_scope("outdated_diff_note") == "outdated_diff_note"

    def test_case_insensitive_scope(self):
        """Should be case-insensitive."""
        assert validate_scope("NOTE") == "note"
        assert validate_scope("DIFF_NOTE") == "diff_note"

    def test_invalid_scope(self):
        """Should reject invalid scope."""
        with pytest.raises(ValidationError, match="scope"):
            validate_scope("invalid")

    def test_typo_scope(self):
        """Should reject typos."""
        with pytest.raises(ValidationError):
            validate_scope("old_diff_note")  # Missing 'utdate' prefix


class TestValidatePositiveInt:
    """Tests for validate_positive_int."""

    def test_positive_int(self):
        """Should accept positive integers."""
        assert validate_positive_int(1) == 1
        assert validate_positive_int(100) == 100
        assert validate_positive_int(999999) == 999999

    def test_zero_not_positive(self):
        """Should reject zero."""
        with pytest.raises(ValidationError, match="positive"):
            validate_positive_int(0)

    def test_negative_not_positive(self):
        """Should reject negative integers."""
        with pytest.raises(ValidationError, match="positive"):
            validate_positive_int(-1)
        with pytest.raises(ValidationError, match="positive"):
            validate_positive_int(-999)

    def test_non_integer(self):
        """Should reject non-integers."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_positive_int(1.5)  # type: ignore

    def test_string_integer(self):
        """Should reject string representation of integer."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_positive_int("1")  # type: ignore

    def test_custom_parameter_name(self):
        """Should include custom parameter name in error."""
        with pytest.raises(ValidationError, match="count"):
            validate_positive_int(-1, name="count")


class TestValidateNonNegativeInt:
    """Tests for validate_non_negative_int."""

    def test_positive_int(self):
        """Should accept positive integers."""
        assert validate_non_negative_int(1) == 1
        assert validate_non_negative_int(100) == 100

    def test_zero_is_non_negative(self):
        """Should accept zero."""
        assert validate_non_negative_int(0) == 0

    def test_negative_rejected(self):
        """Should reject negative integers."""
        with pytest.raises(ValidationError, match="non-negative"):
            validate_non_negative_int(-1)

    def test_non_integer(self):
        """Should reject non-integers."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_non_negative_int(1.5)  # type: ignore

    def test_custom_parameter_name(self):
        """Should include custom parameter name in error."""
        with pytest.raises(ValidationError, match="index"):
            validate_non_negative_int(-1, name="index")


class TestValidateStringLength:
    """Tests for validate_string_length."""

    def test_valid_string(self):
        """Should accept valid strings."""
        assert validate_string_length("hello") == "hello"

    def test_empty_string_allowed(self):
        """Should allow empty string by default."""
        assert validate_string_length("") == ""

    def test_min_length(self):
        """Should enforce minimum length."""
        assert validate_string_length("hello", min_length=5) == "hello"
        with pytest.raises(ValidationError, match="at least"):
            validate_string_length("hi", min_length=5)

    def test_max_length(self):
        """Should enforce maximum length."""
        assert validate_string_length("hello", max_length=5) == "hello"
        with pytest.raises(ValidationError, match="at most"):
            validate_string_length("hello world", max_length=5)

    def test_min_and_max_length(self):
        """Should enforce both min and max."""
        assert validate_string_length("hello", min_length=3, max_length=10) == "hello"
        with pytest.raises(ValidationError, match="at least"):
            validate_string_length("hi", min_length=3, max_length=10)
        with pytest.raises(ValidationError, match="at most"):
            validate_string_length("hello world!!!", min_length=3, max_length=10)

    def test_non_string(self):
        """Should reject non-strings."""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_string_length(123)  # type: ignore

    def test_custom_parameter_name(self):
        """Should include custom parameter name in error."""
        with pytest.raises(ValidationError, match="description"):
            validate_string_length("hi", min_length=5, name="description")

    def test_unicode_string(self):
        """Should handle unicode strings."""
        assert validate_string_length("你好世界") == "你好世界"
        assert validate_string_length("🎉🎊", min_length=2) == "🎉🎊"
