"""Base model classes and shared utilities."""

from datetime import datetime, timezone
from typing import Annotated, overload

from gitlab.base import RESTObject
from pydantic import BaseModel, ConfigDict, PlainSerializer, field_validator

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


def safe_str(text: str | None) -> str:
    """Safely convert text to string, handling None."""
    return text or ""


class BaseGitLabModel(BaseModel):
    """Base class for all GitLab response models.

    Provides common configuration for JSON serialization, validation helpers,
    and timezone handling for all GitLab API response models.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()},
        ser_json_timedelta="float",
    )

    @field_validator("*", mode="before")
    @classmethod
    def validate_none_strings(cls, v):
        """Convert empty strings to None for consistency."""
        if isinstance(v, str) and v == "":
            return None
        return v

    @overload
    @classmethod
    def from_gitlab(cls, obj: RESTObject) -> Self: ...

    @overload
    @classmethod
    def from_gitlab(cls, obj: list[RESTObject]) -> list[Self]: ...

    @classmethod
    def from_gitlab(cls, obj: RESTObject | list[RESTObject]) -> Self | list[Self]:
        """Transform GitLab API object(s) to model instance(s).

        IMPORTANT: This method expects GitLab RESTObject instances ONLY.
        Plain dicts are NOT allowed - use model_validate() for dicts.
        Runtime enforcement prevents dict usage.

        Args:
            obj: GitLab API RESTObject or list of RESTObjects

        Returns:
            Model instance or list of instances

        Raises:
            TypeError: If obj is a plain dict instead of a RESTObject

        Examples:
            # ✅ Single object
            issue = project.issues.get(1)
            summary = IssueSummary.from_gitlab(issue)

            # ✅ List of objects
            issues = project.issues.list()
            summaries = IssueSummary.from_gitlab(issues)

            # ❌ Wrong - plain dict (raises TypeError)
            summary = IssueSummary.from_gitlab({"iid": 1})

            # ✅ For dicts, use model_validate
            summary = IssueSummary.model_validate({"iid": 1})
        """
        # Handle list of objects
        if isinstance(obj, list):
            return [cls.from_gitlab(item) for item in obj]

        # Reject plain dicts
        if isinstance(obj, dict) and not hasattr(obj, '__dict__'):
            raise TypeError(
                f"from_gitlab() expects a GitLab RESTObject, not a plain dict. "
                f"Use {cls.__name__}.model_validate() for dict construction."
            )

        return cls.model_validate(obj, from_attributes=True)


def relative_time(dt: datetime | str | None) -> str:
    """Format datetime as human-readable relative time (English only).

    Args:
        dt: DateTime object, ISO string, or None

    Returns:
        Relative time string like "2 hours ago", "just now"

    Examples:
        >>> relative_time("2024-01-15T10:30:00Z")
        "2 hours ago"
    """
    if dt is None:
        return "unknown"

    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    seconds = (now - dt).total_seconds()

    if seconds < 0:
        return "in the future"
    elif seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} minute ago" if mins == 1 else f"{mins} minutes ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week ago" if weeks == 1 else f"{weeks} weeks ago"
    else:
        months = int(seconds / 2592000)
        return f"{months} month ago" if months == 1 else f"{months} months ago"


def format_timestamp_with_relative(dt: datetime | str | None) -> str:
    """Format timestamp as 'relative time (ISO8601)'.

    Args:
        dt: DateTime object, ISO string, or None

    Returns:
        Combined format like "2 hours ago (2024-01-15T10:30:00Z)"

    Examples:
        >>> format_timestamp_with_relative("2024-01-15T10:30:00Z")
        "2 hours ago (2024-01-15T10:30:00Z)"
    """
    if dt is None:
        return "unknown"

    if isinstance(dt, str):
        iso_str = dt
        dt_obj = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    else:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        iso_str = dt.isoformat().replace("+00:00", "Z")
        dt_obj = dt

    relative = relative_time(dt_obj)
    return f"{relative} ({iso_str})"


# Type alias for timestamp fields: formats as "relative (ISO8601)"
RelativeTime = Annotated[
    str,
    PlainSerializer(lambda v: format_timestamp_with_relative(v), return_type=str),
]

# Type alias for optional timestamp fields
RelativeTimeOptional = Annotated[
    str | None,
    PlainSerializer(
        lambda v: format_timestamp_with_relative(v) if v else None, return_type=str | None
    ),
]

# Type alias for string fields that should convert None to empty string
SafeString = Annotated[
    str | None,
    PlainSerializer(lambda v: safe_str(v), return_type=str),
]
