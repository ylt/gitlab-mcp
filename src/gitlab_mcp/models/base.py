"""Base model classes and shared utilities."""

from datetime import datetime, timezone

from gitlab.base import RESTObject
from pydantic import BaseModel, ConfigDict, field_validator

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

    @classmethod
    def from_gitlab(cls, obj: RESTObject) -> Self:
        """Transform GitLab API object to model instance.

        IMPORTANT: This method expects GitLab RESTObject instances ONLY.
        Plain dicts are NOT allowed - use model_validate() for dicts.
        Runtime enforcement prevents dict usage.

        Type hint is Any to avoid python-gitlab TypeVar issues with type checkers,
        but runtime check enforces RESTObject requirement.

        Args:
            obj: GitLab API RESTObject (e.g., from project.issues.get())

        Returns:
            Model instance with fields populated from obj

        Raises:
            TypeError: If obj is a plain dict instead of a RESTObject

        Examples:
            # ✅ Correct - GitLab API object
            issue = project.issues.get(1)
            summary = IssueSummary.from_gitlab(issue)

            # ❌ Wrong - plain dict (raises TypeError)
            summary = IssueSummary.from_gitlab({"iid": 1})

            # ✅ For dicts, use model_validate
            summary = IssueSummary.model_validate({"iid": 1})
        """
        if isinstance(obj, dict) and not hasattr(obj, '__dict__'):
            raise TypeError(
                f"from_gitlab() expects a GitLab RESTObject, not a plain dict. "
                f"Use {cls.__name__}.model_validate() for dict construction."
            )
        return cls.model_validate(obj, from_attributes=True)


def relative_time(dt: datetime | str | None, locale: str = "en") -> str:
    """Format datetime as human-readable relative time.

    Handles both past and future dates with locale support for time units.

    Args:
        dt: DateTime object, ISO string, or None
        locale: Language locale ("en", "es", "fr", "de"). Defaults to "en".

    Examples: "2 hours ago", "3 days in the future", "just now"
    """
    if dt is None:
        return "unknown"

    if isinstance(dt, str):
        # Handle ISO format with Z suffix
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()

    # Locale-specific time unit translations
    locales = {
        "en": {
            "just_now": "just now",
            "minute_singular": "minute ago",
            "minute_plural": "minutes ago",
            "hour_singular": "hour ago",
            "hour_plural": "hours ago",
            "day_singular": "day ago",
            "day_plural": "days ago",
            "week_singular": "week ago",
            "week_plural": "weeks ago",
            "month_singular": "month ago",
            "month_plural": "months ago",
            "in_future_singular": "in the future",
            "in_future_plural": "in the future",
        },
        "es": {
            "just_now": "justo ahora",
            "minute_singular": "hace un minuto",
            "minute_plural": "hace {n} minutos",
            "hour_singular": "hace una hora",
            "hour_plural": "hace {n} horas",
            "day_singular": "hace un día",
            "day_plural": "hace {n} días",
            "week_singular": "hace una semana",
            "week_plural": "hace {n} semanas",
            "month_singular": "hace un mes",
            "month_plural": "hace {n} meses",
            "in_future_singular": "en el futuro",
            "in_future_plural": "en el futuro",
        },
        "fr": {
            "just_now": "à l'instant",
            "minute_singular": "il y a une minute",
            "minute_plural": "il y a {n} minutes",
            "hour_singular": "il y a une heure",
            "hour_plural": "il y a {n} heures",
            "day_singular": "il y a un jour",
            "day_plural": "il y a {n} jours",
            "week_singular": "il y a une semaine",
            "week_plural": "il y a {n} semaines",
            "month_singular": "il y a un mois",
            "month_plural": "il y a {n} mois",
            "in_future_singular": "dans le futur",
            "in_future_plural": "dans le futur",
        },
        "de": {
            "just_now": "gerade eben",
            "minute_singular": "vor einer Minute",
            "minute_plural": "vor {n} Minuten",
            "hour_singular": "vor einer Stunde",
            "hour_plural": "vor {n} Stunden",
            "day_singular": "vor einem Tag",
            "day_plural": "vor {n} Tagen",
            "week_singular": "vor einer Woche",
            "week_plural": "vor {n} Wochen",
            "month_singular": "vor einem Monat",
            "month_plural": "vor {n} Monaten",
            "in_future_singular": "in der Zukunft",
            "in_future_plural": "in der Zukunft",
        },
    }

    loc = locales.get(locale, locales["en"])

    # Handle future dates
    if seconds < 0:
        return loc["in_future_singular"]

    if seconds < 60:
        return loc["just_now"]
    elif seconds < 3600:
        mins = int(seconds / 60)
        key = "minute_singular" if mins == 1 else "minute_plural"
        return loc[key].format(n=mins) if "{n}" in loc[key] else loc[key]
    elif seconds < 86400:
        hours = int(seconds / 3600)
        key = "hour_singular" if hours == 1 else "hour_plural"
        return loc[key].format(n=hours) if "{n}" in loc[key] else loc[key]
    elif seconds < 604800:
        days = int(seconds / 86400)
        key = "day_singular" if days == 1 else "day_plural"
        return loc[key].format(n=days) if "{n}" in loc[key] else loc[key]
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        key = "week_singular" if weeks == 1 else "week_plural"
        return loc[key].format(n=weeks) if "{n}" in loc[key] else loc[key]
    else:
        months = int(seconds / 2592000)
        key = "month_singular" if months == 1 else "month_plural"
        return loc[key].format(n=months) if "{n}" in loc[key] else loc[key]
