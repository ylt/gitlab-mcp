"""Type stubs for gitlab.base."""

from typing import Any, TypeVar

_T = TypeVar("_T", bound="RESTObject")

class RESTObject:
    """Base class for GitLab REST objects."""

    def __init__(self, manager: Any, attrs: dict[str, Any]) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...
