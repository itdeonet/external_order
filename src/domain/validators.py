"""Domain validation utilities for frozen dataclasses.

This module provides a collection of validation and normalization functions
used across domain model classes. These utilities enforce data integrity by
validating inputs at construction time and normalizing strings appropriately.

Validation functions check that values meet domain requirements and raise
ValueError with descriptive messages if validation fails. Used extensively in
__post_init__ methods of frozen dataclasses to ensure invalid objects cannot
be created.

Normalization functions transform string values (trimming whitespace, changing
case, etc.) as needed by domain models. Some validation functions (like
validate_email) both validate and normalize in a single operation.

Key patterns:
- validate_*: Check value correctness, raise ValueError if invalid
- validate_optional_*: Return normalized value or empty string
- set_*: Apply object.__setattr__ for frozen dataclass field updates

Example usage in a frozen dataclass:
    >>> def __post_init__(self):
    ...     validators.validate_positive_int(self.quantity, "Quantity")
    ...     validators.validate_non_empty_string(self.name, "Name")
    ...     normalized = validators.validate_email(self.email)
    ...     object.__setattr__(self, "email", normalized)
"""

from typing import Any


def validate_positive_int(value: Any, field_name: str) -> None:
    """Validate that a value is a positive integer.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Raises:
        ValueError: If the value is not a positive integer.
    """
    if not (isinstance(value, int) and value > 0):
        raise ValueError(f"{field_name} must be a positive integer.")


def validate_non_negative_int(value: Any, field_name: str) -> None:
    """Validate that a value is a non-negative integer.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Raises:
        ValueError: If the value is not a non-negative integer.
    """
    if not (isinstance(value, int) and value >= 0):
        raise ValueError(f"{field_name} must be a non-negative integer.")


def validate_non_empty_string(value: Any, field_name: str) -> str:
    """Validate and normalize a non-empty string.

    Strips whitespace from the string.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated string, stripped of whitespace.

    Raises:
        ValueError: If the value is not a non-empty string.
    """
    if not (isinstance(value, str) and value.strip()):
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def validate_non_empty_string_uppercase(value: Any, field_name: str) -> str:
    """Validate and normalize a non-empty string to uppercase.

    Strips whitespace and converts to uppercase.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated string, stripped and converted to uppercase.

    Raises:
        ValueError: If the value is not a non-empty string.
    """
    normalized = validate_non_empty_string(value, field_name)
    return normalized.upper()


def validate_non_empty_string_lowercase(value: Any, field_name: str) -> str:
    """Validate and normalize a non-empty string to lowercase.

    Strips whitespace and converts to lowercase.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated string, stripped and converted to lowercase.

    Raises:
        ValueError: If the value is not a non-empty string.
    """
    normalized = validate_non_empty_string(value, field_name)
    return normalized.lower()


def validate_optional_string(value: Any, field_name: str) -> str:
    """Validate and normalize an optional string.

    Returns empty string if value is not a non-empty string, otherwise strips whitespace.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated string, stripped of whitespace, or empty string if not valid.
    """
    if isinstance(value, str):
        return value.strip()
    return ""


def validate_optional_string_uppercase(value: Any, field_name: str) -> str:
    """Validate and normalize an optional string to uppercase.

    Returns empty string if value is not a non-empty string, otherwise strips and uppercases.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated string, stripped and uppercased, or empty string if not valid.
    """
    normalized = validate_optional_string(value, field_name)
    return normalized.upper() if normalized else ""


def validate_instance[T](value: Any, expected_type: type[T], field_name: str) -> None:
    """Validate that a value is an instance of a specific type.

    Args:
        value: The value to validate.
        expected_type: The expected type.
        field_name: The name of the field being validated (for error messages).

    Raises:
        ValueError: If the value is not an instance of the expected type.
    """
    if not isinstance(value, expected_type):
        raise ValueError(f"{field_name} must be an instance of {expected_type.__name__}.")


def validate_list_of_instances[T](
    value: Any, expected_type: type[T], field_name: str, allow_empty: bool = False
) -> None:
    """Validate that a value is a non-empty list of instances of a specific type.

    Args:
        value: The value to validate.
        expected_type: The expected type of list items.
        field_name: The name of the field being validated (for error messages).
        allow_empty: If True, allows empty lists. If False, requires at least one item.

    Raises:
        ValueError: If the value is not a valid list.
    """
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list.")

    if not allow_empty and not value:
        raise ValueError(f"{field_name} cannot be empty.")

    if not all(isinstance(item, expected_type) for item in value):
        raise ValueError(f"{field_name} must contain only instances of {expected_type.__name__}.")


def validate_email(value: Any, field_name: str = "Email") -> str:
    """Validate and normalize an email address.

    Performs basic email validation (contains @ and .) and normalizes to lowercase.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated email, normalized to lowercase.

    Raises:
        ValueError: If the value is not a valid email.
    """
    if not (isinstance(value, str) and value.strip()):
        raise ValueError(f"{field_name} must be a non-empty string.")

    email = value.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError(f"{field_name} must be a valid email address.")

    return email


def validate_phone(value: Any, field_name: str = "Phone") -> str:
    """Validate and normalize a phone number.

    Allows digits and valid phone characters (+, -, (, ), space).

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated phone number, stripped of whitespace.

    Raises:
        ValueError: If the value is not a valid phone number.
    """
    if not (isinstance(value, str) and value.strip()):
        raise ValueError(f"{field_name} must be a non-empty string.")

    phone = value.strip()
    if not all(c.isdigit() or c in "+-() " for c in phone):
        raise ValueError(f"{field_name} must contain only digits and valid characters.")

    return phone


def validate_country_code(value: Any, field_name: str = "Country code") -> str:
    """Validate and normalize a 2-letter ISO country code.

    Converts to uppercase.

    Args:
        value: The value to validate.
        field_name: The name of the field being validated (for error messages).

    Returns:
        The validated country code, converted to uppercase.

    Raises:
        ValueError: If the value is not a valid 2-letter country code.
    """
    if not (isinstance(value, str) and len(value.strip()) == 2):
        raise ValueError(f"{field_name} must be a 2-letter ISO code.")

    return value.strip().upper()


def set_stripped_string(obj: Any, field_name: str, value: str) -> None:
    """Set a stripped string value on a frozen dataclass.

    Args:
        obj: The frozen dataclass instance.
        field_name: The name of the field to set.
        value: The value to set (will be stripped).
    """
    object.__setattr__(obj, field_name, value.strip())


def set_normalized_string(obj: Any, field_name: str, value: str, transform: str = "none") -> None:
    """Set a normalized string value on a frozen dataclass.

    Args:
        obj: The frozen dataclass instance.
        field_name: The name of the field to set.
        value: The value to set (will be stripped).
        transform: Transformation to apply: "none", "upper", or "lower".
    """
    stripped = value.strip()
    if transform == "upper":
        stripped = stripped.upper()
    elif transform == "lower":
        stripped = stripped.lower()
    object.__setattr__(obj, field_name, stripped)
