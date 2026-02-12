"""Tests for query building utilities."""

from datetime import datetime, timezone

import pytest

from gitlab_mcp.utils.query import build_filters, build_sort


class TestBuildFilters:
    """Tests for build_filters function."""

    def test_empty_filters(self):
        """Test build_filters with no arguments returns empty dict."""
        result = build_filters()
        assert result == {}

    def test_single_filter(self):
        """Test build_filters with a single filter."""
        result = build_filters(state="opened")
        assert result == {"state": "opened"}

    def test_multiple_filters(self):
        """Test build_filters with multiple filters."""
        result = build_filters(
            state="closed",
            author_id=123,
            assignee_id=456,
        )
        assert result == {
            "state": "closed",
            "author_id": 123,
            "assignee_id": 456,
        }

    def test_none_values_excluded(self):
        """Test that None values are excluded from result."""
        result = build_filters(
            state="opened",
            author_id=None,
            assignee_id=456,
        )
        assert result == {
            "state": "opened",
            "assignee_id": 456,
        }
        assert "author_id" not in result

    def test_labels_joined(self):
        """Test that labels list is converted to comma-separated string."""
        result = build_filters(labels=["bug", "feature", "urgent"])
        assert result == {"labels": "bug,feature,urgent"}

    def test_empty_labels_list(self):
        """Test that empty labels list is excluded."""
        result = build_filters(labels=[])
        assert result == {}

    def test_single_label(self):
        """Test labels with single item."""
        result = build_filters(labels=["bug"])
        assert result == {"labels": "bug"}

    def test_datetime_object_conversion(self):
        """Test that datetime objects are converted to ISO format strings."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = build_filters(created_after=dt)
        assert result == {"created_after": "2024-01-15T10:30:45+00:00"}

    def test_multiple_datetime_filters(self):
        """Test multiple datetime filters."""
        dt1 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        result = build_filters(
            created_after=dt1,
            created_before=dt2,
            updated_after=dt1,
            updated_before=dt2,
        )
        assert result == {
            "created_after": "2024-01-01T00:00:00+00:00",
            "created_before": "2024-01-31T23:59:59+00:00",
            "updated_after": "2024-01-01T00:00:00+00:00",
            "updated_before": "2024-01-31T23:59:59+00:00",
        }

    def test_string_datetime_passed_through(self):
        """Test that string datetime values are passed through as-is."""
        iso_string = "2024-01-15T10:30:45Z"
        result = build_filters(created_after=iso_string)
        assert result == {"created_after": iso_string}

    def test_all_filters_combined(self):
        """Test with all filter types together."""
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = build_filters(
            state="opened",
            author_id=1,
            author_username="alice",
            assignee_id=2,
            labels=["bug", "critical"],
            milestone="v1.0",
            search="urgent fix",
            created_after=dt,
            updated_before="2024-02-01",
        )
        assert result == {
            "state": "opened",
            "author_id": 1,
            "author_username": "alice",
            "assignee_id": 2,
            "labels": "bug,critical",
            "milestone": "v1.0",
            "search": "urgent fix",
            "created_after": "2024-01-01T00:00:00+00:00",
            "updated_before": "2024-02-01",
        }

    def test_extra_filters_included(self):
        """Test that extra keyword arguments are included if non-None."""
        result = build_filters(
            state="opened",
            custom_field="custom_value",
            another_field=123,
        )
        assert result == {
            "state": "opened",
            "custom_field": "custom_value",
            "another_field": 123,
        }

    def test_extra_filters_none_excluded(self):
        """Test that None values in extra filters are excluded."""
        result = build_filters(
            state="opened",
            custom_field=None,
            another_field=456,
        )
        assert result == {
            "state": "opened",
            "another_field": 456,
        }

    def test_milestone_none(self):
        """Test milestone filter with None."""
        result = build_filters(milestone=None, state="opened")
        assert result == {"state": "opened"}
        assert "milestone" not in result

    def test_search_with_special_characters(self):
        """Test search filter with special characters."""
        result = build_filters(search="fix: bug & feature [WIP]")
        assert result == {"search": "fix: bug & feature [WIP]"}


class TestBuildSort:
    """Tests for build_sort function."""

    def test_empty_sort(self):
        """Test build_sort with no arguments returns empty dict."""
        result = build_sort()
        assert result == {}

    def test_order_by_only(self):
        """Test build_sort with only order_by."""
        result = build_sort(order_by="created_at")
        assert result == {
            "order_by": "created_at",
            "sort": "desc",
        }

    def test_order_by_with_asc(self):
        """Test build_sort with order_by and ascending sort."""
        result = build_sort(order_by="title", sort="asc")
        assert result == {
            "order_by": "title",
            "sort": "asc",
        }

    def test_order_by_with_desc(self):
        """Test build_sort with order_by and descending sort."""
        result = build_sort(order_by="updated_at", sort="desc")
        assert result == {
            "order_by": "updated_at",
            "sort": "desc",
        }

    def test_none_order_by(self):
        """Test build_sort with None order_by returns empty dict."""
        result = build_sort(order_by=None, sort="asc")
        assert result == {}

    def test_invalid_sort_direction(self):
        """Test build_sort with invalid sort direction raises ValueError."""
        with pytest.raises(ValueError, match="sort must be 'asc' or 'desc'"):
            build_sort(order_by="created_at", sort="invalid")

    def test_invalid_sort_uppercase(self):
        """Test build_sort rejects uppercase sort values."""
        with pytest.raises(ValueError, match="sort must be 'asc' or 'desc'"):
            build_sort(order_by="created_at", sort="DESC")

    def test_common_sort_fields(self):
        """Test build_sort with commonly used fields."""
        for field in ["created_at", "updated_at", "title", "priority"]:
            result = build_sort(order_by=field, sort="desc")
            assert result == {"order_by": field, "sort": "desc"}
