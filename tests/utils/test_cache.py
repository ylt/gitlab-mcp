"""Tests for caching utilities."""

import time


from gitlab_mcp.utils.cache import cached, clear_cache, invalidate


class TestCached:
    """Test the @cached decorator."""

    def test_caching_works(self):
        """Test that caching stores and returns values."""
        call_count = 0

        @cached(ttl=300)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call with same args should return cached value
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Call with different args should execute function again
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

        clear_cache()

    def test_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        call_count = 0

        @cached(ttl=1)
        def short_ttl_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = short_ttl_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call within TTL (should use cache)
        result2 = short_ttl_function(5)
        assert result2 == 10
        assert call_count == 1

        # Wait for TTL to expire
        time.sleep(1.1)

        # Third call after TTL expiration (should execute function)
        result3 = short_ttl_function(5)
        assert result3 == 10
        assert call_count == 2

        clear_cache()

    def test_caching_with_kwargs(self):
        """Test caching with keyword arguments."""
        call_count = 0

        @cached(ttl=300)
        def function_with_kwargs(a: int, b: int = 10) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        # Call with same args and kwargs
        result1 = function_with_kwargs(5, b=10)
        assert result1 == 15
        assert call_count == 1

        result2 = function_with_kwargs(5, b=10)
        assert result2 == 15
        assert call_count == 1  # Cached

        # Call with different kwargs should execute function
        result3 = function_with_kwargs(5, b=20)
        assert result3 == 25
        assert call_count == 2

        clear_cache()

    def test_caching_with_string_args(self):
        """Test caching with string arguments."""
        call_count = 0

        @cached(ttl=300)
        def lookup_namespace(path: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"path": path, "id": 123}

        # First call
        result1 = lookup_namespace("my/namespace")
        assert result1 == {"path": "my/namespace", "id": 123}
        assert call_count == 1

        # Second call with same arg
        result2 = lookup_namespace("my/namespace")
        assert result2 == {"path": "my/namespace", "id": 123}
        assert call_count == 1

        clear_cache()


class TestClearCache:
    """Test the clear_cache function."""

    def test_clear_cache_removes_all_entries(self):
        """Test that clear_cache removes all cached values."""
        call_count = 0

        @cached(ttl=300)
        def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # Cache some values
        test_function(1)
        test_function(2)
        test_function(3)
        assert call_count == 3

        # Clear cache
        clear_cache()

        # Calls should execute function again
        test_function(1)
        test_function(2)
        test_function(3)
        assert call_count == 6

    def test_clear_cache_on_empty_cache(self):
        """Test that clear_cache works on empty cache without error."""
        clear_cache()  # Should not raise any exception


class TestInvalidate:
    """Test the invalidate function."""

    def test_invalidate_by_prefix(self):
        """Test invalidating cache entries by prefix."""
        call_count_ns = 0
        call_count_user = 0

        @cached(ttl=300)
        def get_namespace(path: str) -> dict:
            nonlocal call_count_ns
            call_count_ns += 1
            return {"path": path}

        @cached(ttl=300)
        def get_user(username: str) -> dict:
            nonlocal call_count_user
            call_count_user += 1
            return {"username": username}

        # Cache some values
        get_namespace("path1")
        get_namespace("path2")
        get_user("user1")
        get_user("user2")
        assert call_count_ns == 2
        assert call_count_user == 2

        # Invalidate namespace entries
        invalidate("get_namespace")

        # Namespace calls should re-execute
        get_namespace("path1")
        get_namespace("path2")
        assert call_count_ns == 4  # Re-executed

        # User calls should still be cached
        get_user("user1")
        get_user("user2")
        assert call_count_user == 2  # Still cached

        clear_cache()

    def test_invalidate_no_matching_entries(self):
        """Test invalidate with prefix that matches no entries."""
        call_count = 0

        @cached(ttl=300)
        def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # Cache a value
        test_function(1)
        assert call_count == 1

        # Invalidate with non-matching prefix (should do nothing)
        invalidate("nonexistent_prefix")

        # Call should still be cached
        test_function(1)
        assert call_count == 1

        clear_cache()

    def test_invalidate_partial_prefix_match(self):
        """Test that invalidate matches prefixes correctly."""
        call_count = 0

        @cached(ttl=300)
        def get_namespace_by_id(id: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": id}

        # Cache values
        get_namespace_by_id(1)
        get_namespace_by_id(2)
        assert call_count == 2

        # Invalidate by prefix "get_namespace"
        invalidate("get_namespace")

        # Calls should re-execute
        get_namespace_by_id(1)
        get_namespace_by_id(2)
        assert call_count == 4

        clear_cache()
