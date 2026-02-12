"""Utilities for serializing Pydantic models to JSON for MCP responses."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar
from pydantic import BaseModel


F = TypeVar("F", bound=Callable[..., Any])


def serialize_pydantic(func: F) -> F:
    """Decorator that converts Pydantic models to dicts for MCP responses.

    Allows tool functions to return typed Pydantic models while automatically
    handling JSON serialization for the MCP protocol.

    Handles:
    - Single Pydantic model → model.model_dump()
    - List of Pydantic models → [m.model_dump() for m in models]
    - Plain dicts/primitives → pass through unchanged

    Example:
        @mcp.tool
        @serialize_pydantic
        def get_merge_request(...) -> MergeRequestSummary:
            return MergeRequestSummary.model_validate(mr, from_attributes=True)  # Returns Pydantic model
            # Decorator automatically converts to dict for MCP
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)

        # Single Pydantic model
        if isinstance(result, BaseModel):
            return result.model_dump(by_alias=True)

        # List of Pydantic models
        if isinstance(result, list) and result and isinstance(result[0], BaseModel):
            return [item.model_dump(by_alias=True) for item in result]

        # Pass through anything else (dicts, primitives, None)
        return result

    return wrapper  # type: ignore[return-value]
