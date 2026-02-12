"""Simple TTL-based caching utilities."""

import time
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# Simple in-memory cache store
_cache: dict[str, tuple[Any, float]] = {}


def cached(ttl: int = 300):
    """Decorator for TTL-based caching.

    Args:
        ttl: Time-to-live in seconds (default 5 minutes)

    Usage:
        @cached(ttl=300)
        def get_namespace(path: str) -> dict:
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Build cache key from function name + args + kwargs
            key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"

            # Check cache
            if key in _cache:
                value, expiry = _cache[key]
                if time.time() < expiry:
                    return value

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache[key] = (result, time.time() + ttl)
            return result

        return wrapper

    return decorator


def clear_cache() -> None:
    """Clear all cached values."""
    _cache.clear()


def invalidate(prefix: str) -> None:
    """Invalidate cache entries matching prefix.

    Args:
        prefix: Prefix to match in cache keys (e.g., "get_namespace")
    """
    keys_to_delete = [k for k in _cache if k.startswith(prefix)]
    for k in keys_to_delete:
        del _cache[k]
