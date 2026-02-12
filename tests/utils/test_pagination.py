"""Tests for pagination utilities."""

from unittest.mock import Mock
from gitlab_mcp.utils.pagination import paginate


class TestPaginate:
    """Tests for the paginate() function."""

    def test_basic_pagination_single_page(self):
        """Test pagination returns single page of results."""
        # Mock manager with single page of results
        manager = Mock()
        items = [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]
        manager.list.return_value = items

        result = paginate(manager, per_page=20)

        assert result == items
        manager.list.assert_called_once_with(page=1, per_page=20)

    def test_per_page_clamped_to_max(self):
        """Test that per_page is clamped to GitLab's max of 100."""
        manager = Mock()
        manager.list.return_value = []

        paginate(manager, per_page=200)

        # Should be called with per_page=100, not 200
        manager.list.assert_called_once()
        call_kwargs = manager.list.call_args[1]
        assert call_kwargs["per_page"] == 100

    def test_per_page_minimum_is_one(self):
        """Test that per_page has a minimum of 1."""
        manager = Mock()
        manager.list.return_value = []

        paginate(manager, per_page=0)

        call_kwargs = manager.list.call_args[1]
        assert call_kwargs["per_page"] == 1

    def test_filters_passed_to_list(self):
        """Test that additional filters are passed to the list() call."""
        manager = Mock()
        manager.list.return_value = []

        paginate(
            manager,
            per_page=20,
            state="opened",
            author_id=123,
            labels="bug",
        )

        call_kwargs = manager.list.call_args[1]
        assert call_kwargs["state"] == "opened"
        assert call_kwargs["author_id"] == 123
        assert call_kwargs["labels"] == "bug"

    def test_empty_result_set(self):
        """Test pagination with no results."""
        manager = Mock()
        manager.list.return_value = []

        result = paginate(manager, per_page=20)

        assert result == []
        manager.list.assert_called_once()

    def test_default_per_page(self):
        """Test that default per_page is 20."""
        manager = Mock()
        manager.list.return_value = []

        paginate(manager)

        call_kwargs = manager.list.call_args[1]
        assert call_kwargs["per_page"] == 20

    def test_single_api_call(self):
        """Test that pagination makes exactly one API call."""
        manager = Mock()
        items = [{"id": i} for i in range(1, 51)]
        manager.list.return_value = items

        result = paginate(manager, per_page=50)

        assert len(result) == 50
        manager.list.assert_called_once()

    def test_partial_page_result(self):
        """Test pagination returns partial page correctly."""
        manager = Mock()
        items = [{"id": i} for i in range(1, 6)]  # Only 5 items
        manager.list.return_value = items

        result = paginate(manager, per_page=20)

        assert len(result) == 5
        assert result[0]["id"] == 1
        assert result[4]["id"] == 5
        manager.list.assert_called_once()
