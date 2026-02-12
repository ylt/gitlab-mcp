"""Input validation utilities."""

import re
from datetime import datetime


class ValidationError(ValueError):
    """Raised when validation fails."""

    pass


def validate_color(color: str) -> str:
    """Validate and normalize a hex color code.

    Args:
        color: Hex color like "#FF0000" or "FF0000"

    Returns:
        Normalized color without # prefix (e.g., "FF0000")

    Raises:
        ValidationError: If color format is invalid
    """
    if not color:
        raise ValidationError("color cannot be empty")

    # Strip # prefix if present
    normalized = color.lstrip("#")

    # Validate 6 hex characters
    if not re.match(r"^[0-9a-fA-F]{6}$", normalized):
        raise ValidationError(
            f"Invalid color format: {color}. Must be 6 hex digits (e.g., FF0000 or #FF0000)"
        )

    # Return uppercase normalized
    return normalized.upper()


def validate_date(date: str | datetime) -> str:
    """Validate and normalize a date to ISO format.

    Args:
        date: Date string (YYYY-MM-DD) or datetime object

    Returns:
        ISO format date string (YYYY-MM-DD)

    Raises:
        ValidationError: If date format is invalid
    """
    if isinstance(date, datetime):
        return date.strftime("%Y-%m-%d")

    if not isinstance(date, str):
        raise ValidationError(f"Date must be string or datetime, got {type(date).__name__}")

    if not date:
        raise ValidationError("date cannot be empty")

    # Try to parse as ISO format YYYY-MM-DD
    try:
        parsed = datetime.strptime(date, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"Invalid date format: {date}. Must be YYYY-MM-DD (e.g., 2024-01-15)")


def validate_format(value: str, allowed: list[str], name: str = "value") -> str:
    """Validate that value is one of the allowed options.

    Args:
        value: The value to validate
        allowed: List of allowed values
        name: Name of the parameter (for error messages)

    Returns:
        The validated value (lowercase)

    Raises:
        ValidationError: If value not in allowed list
    """
    if not value:
        raise ValidationError(f"{name} cannot be empty")

    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string, got {type(value).__name__}")

    normalized = value.lower()
    allowed_lower = [a.lower() for a in allowed]

    if normalized not in allowed_lower:
        raise ValidationError(f"Invalid {name}: {value}. Must be one of: {', '.join(allowed)}")

    return normalized


def validate_state(state: str) -> str:
    """Validate MR/Issue state (opened, closed, merged, all).

    Args:
        state: State value to validate

    Returns:
        The validated state (lowercase)

    Raises:
        ValidationError: If state is invalid
    """
    return validate_format(state, ["opened", "closed", "merged", "all"], name="state")


def validate_scope(scope: str) -> str:
    """Validate discussion scope (note, diff_note, outdate_diff_note).

    Args:
        scope: Scope value to validate

    Returns:
        The validated scope (lowercase)

    Raises:
        ValidationError: If scope is invalid
    """
    return validate_format(
        scope,
        ["note", "diff_note", "outdated_diff_note"],
        name="scope",
    )


def validate_positive_int(value: int, name: str = "value") -> int:
    """Validate that value is a positive integer.

    Args:
        value: The value to validate
        name: Name of the parameter (for error messages)

    Returns:
        The validated value

    Raises:
        ValidationError: If value is not positive
    """
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer, got {type(value).__name__}")

    if value <= 0:
        raise ValidationError(f"{name} must be positive, got {value}")

    return value


def validate_non_negative_int(value: int, name: str = "value") -> int:
    """Validate that value is a non-negative integer.

    Args:
        value: The value to validate
        name: Name of the parameter (for error messages)

    Returns:
        The validated value

    Raises:
        ValidationError: If value is negative
    """
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer, got {type(value).__name__}")

    if value < 0:
        raise ValidationError(f"{name} must be non-negative, got {value}")

    return value


def validate_string_length(
    value: str, min_length: int = 0, max_length: int | None = None, name: str = "value"
) -> str:
    """Validate string length.

    Args:
        value: The string to validate
        min_length: Minimum length (default 0)
        max_length: Maximum length (no limit if None)
        name: Name of the parameter (for error messages)

    Returns:
        The validated string

    Raises:
        ValidationError: If length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string, got {type(value).__name__}")

    if len(value) < min_length:
        raise ValidationError(f"{name} must be at least {min_length} characters, got {len(value)}")

    if max_length is not None and len(value) > max_length:
        raise ValidationError(f"{name} must be at most {max_length} characters, got {len(value)}")

    return value
