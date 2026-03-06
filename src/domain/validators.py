"""Validation and normalization utilities for domain models.

Simple helpers used by dataclass __post_init__ methods to validate and
normalize fields. They raise ValueError on invalid input.
"""

from typing import Any


def validate_positive_int(value: Any, field_name: str) -> None:
    """Raise ValueError if `value` is not a positive int."""
    if not (isinstance(value, int) and value > 0):
        raise ValueError(f"{field_name} must be a positive integer.")


def validate_non_negative_int(value: Any, field_name: str) -> None:
    """Raise ValueError if `value` is not a non-negative int."""
    if not (isinstance(value, int) and value >= 0):
        raise ValueError(f"{field_name} must be a non-negative integer.")


def validate_non_empty_string(value: Any, field_name: str) -> str:
    """Return stripped string; raise ValueError if empty or not a string."""
    if not (isinstance(value, str) and value.strip()):
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def validate_non_empty_string_uppercase(value: Any, field_name: str) -> str:
    """Return stripped, uppercased string; raises on invalid input."""
    normalized = validate_non_empty_string(value, field_name)
    return normalized.upper()


def validate_non_empty_string_lowercase(value: Any, field_name: str) -> str:
    """Return stripped, lowercased string; raises on invalid input."""
    normalized = validate_non_empty_string(value, field_name)
    return normalized.lower()


def validate_optional_string(value: Any, field_name: str) -> str:
    """Return stripped string or empty string if not a string."""
    if isinstance(value, str):
        return value.strip()
    return ""


def validate_optional_string_uppercase(value: Any, field_name: str) -> str:
    """Return stripped uppercased string or empty string if not a string."""
    normalized = validate_optional_string(value, field_name)
    return normalized.upper() if normalized else ""


def validate_instance[T](value: Any, expected_type: type[T], field_name: str) -> None:
    """Raise ValueError if `value` is not an instance of `expected_type`."""
    if not isinstance(value, expected_type):
        raise ValueError(f"{field_name} must be an instance of {expected_type.__name__}.")


def validate_list_of_instances[T](
    value: Any, expected_type: type[T], field_name: str, allow_empty: bool = False
) -> None:
    """Validate list items are instances of `expected_type`; optionally allow empty."""
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list.")

    if not allow_empty and not value:
        raise ValueError(f"{field_name} cannot be empty.")

    if not all(isinstance(item, expected_type) for item in value):
        raise ValueError(f"{field_name} must contain only instances of {expected_type.__name__}.")


def validate_email(value: Any, field_name: str = "Email") -> str:
    """Return normalized lowercase email; raise ValueError if invalid."""
    if not (isinstance(value, str) and value.strip()):
        raise ValueError(f"{field_name} must be a non-empty string.")

    email = value.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError(f"{field_name} must be a valid email address.")

    return email


def validate_phone(value: Any, field_name: str = "Phone") -> str:
    """Return stripped phone string; raise ValueError if contains invalid chars."""
    if not (isinstance(value, str) and value.strip()):
        raise ValueError(f"{field_name} must be a non-empty string.")

    phone = value.strip()
    if not all(c.isdigit() or c in "+-() " for c in phone):
        raise ValueError(f"{field_name} must contain only digits and valid characters.")

    return phone


def validate_country_code(value: Any, field_name: str = "Country code") -> str:
    """Return uppercased 2-letter country code; raise on invalid input."""
    if not (isinstance(value, str) and len(value.strip()) == 2):
        raise ValueError(f"{field_name} must be a 2-letter ISO code.")

    return value.strip().upper()


def set_stripped_string(obj: Any, field_name: str, value: str) -> None:
    """Set a stripped string on a frozen dataclass field."""
    object.__setattr__(obj, field_name, value.strip())


def set_normalized_string(obj: Any, field_name: str, value: str, transform: str = "none") -> None:
    """Set a normalized (stripped, optional case) string on a frozen dataclass."""
    stripped = value.strip()
    if transform == "upper":
        stripped = stripped.upper()
    elif transform == "lower":
        stripped = stripped.lower()
    object.__setattr__(obj, field_name, stripped)
