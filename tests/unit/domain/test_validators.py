"""Unit tests for domain validators."""

import pytest

from src.domain import validators


class TestValidateNonEmptyStringLowercase:
    """Tests for validate_non_empty_string_lowercase."""

    def test_converts_to_lowercase(self):
        """Test that value is converted to lowercase."""
        result = validators.validate_non_empty_string_lowercase("HELLO", "test")
        assert result == "hello"

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = validators.validate_non_empty_string_lowercase("  HELLO  ", "test")
        assert result == "hello"

    def test_raises_on_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="test must be a non-empty string"):
            validators.validate_non_empty_string_lowercase("", "test")

    def test_raises_on_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="test must be a non-empty string"):
            validators.validate_non_empty_string_lowercase(None, "test")

    def test_raises_on_whitespace_only(self):
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="test must be a non-empty string"):
            validators.validate_non_empty_string_lowercase("   ", "test")

    def test_mixed_case_conversion(self):
        """Test conversion of mixed case strings."""
        result = validators.validate_non_empty_string_lowercase("MiXeD_CaSe", "test")
        assert result == "mixed_case"


class TestValidateNonEmptyStringUppercase:
    """Tests for validate_non_empty_string_uppercase."""

    def test_converts_to_uppercase(self):
        """Test that value is converted to uppercase."""
        result = validators.validate_non_empty_string_uppercase("hello", "test")
        assert result == "HELLO"

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = validators.validate_non_empty_string_uppercase("  hello  ", "test")
        assert result == "HELLO"

    def test_raises_on_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="test must be a non-empty string"):
            validators.validate_non_empty_string_uppercase("", "test")

    def test_raises_on_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="test must be a non-empty string"):
            validators.validate_non_empty_string_uppercase(None, "test")

    def test_mixed_case_conversion(self):
        """Test conversion of mixed case strings."""
        result = validators.validate_non_empty_string_uppercase("MiXeD-CaSe", "test")
        assert result == "MIXED-CASE"


class TestValidateOptionalString:
    """Tests for validate_optional_string."""

    def test_returns_string_stripped(self):
        """Test that string is returned stripped."""
        result = validators.validate_optional_string("  hello  ", "test")
        assert result == "hello"

    def test_returns_empty_for_none(self):
        """Test that None returns empty string."""
        result = validators.validate_optional_string(None, "test")
        assert result == ""

    def test_returns_empty_for_empty_string(self):
        """Test that empty string returns empty string."""
        result = validators.validate_optional_string("", "test")
        assert result == ""

    def test_returns_empty_for_whitespace(self):
        """Test that whitespace-only returns empty string."""
        result = validators.validate_optional_string("   ", "test")
        assert result == ""

    def test_returns_empty_for_non_string(self):
        """Test that non-string returns empty string."""
        result = validators.validate_optional_string(123, "test")
        assert result == ""


class TestValidateOptionalStringUppercase:
    """Tests for validate_optional_string_uppercase."""

    def test_returns_uppercase_and_stripped(self):
        """Test that string is returned uppercase and stripped."""
        result = validators.validate_optional_string_uppercase("  hello  ", "test")
        assert result == "HELLO"

    def test_returns_empty_for_none(self):
        """Test that None returns empty string."""
        result = validators.validate_optional_string_uppercase(None, "test")
        assert result == ""

    def test_returns_empty_for_empty_string(self):
        """Test that empty string returns empty string."""
        result = validators.validate_optional_string_uppercase("", "test")
        assert result == ""

    def test_returns_empty_for_whitespace(self):
        """Test that whitespace-only returns empty string."""
        result = validators.validate_optional_string_uppercase("   ", "test")
        assert result == ""


class TestValidatePhone:
    """Tests for validate_phone."""

    def test_accepts_valid_phone(self):
        """Test that valid phone numbers are accepted."""
        result = validators.validate_phone("+1-555-123-4567", "phone")
        assert isinstance(result, str)

    def test_accepts_phone_without_formatting(self):
        """Test that unformatted phone numbers are accepted."""
        result = validators.validate_phone("5551234567", "phone")
        assert isinstance(result, str)

    def test_raises_on_empty_phone(self):
        """Test that empty phone raises ValueError."""
        with pytest.raises(ValueError, match="phone must be a non-empty string"):
            validators.validate_phone("", "phone")

    def test_raises_on_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="phone must be a non-empty string"):
            validators.validate_phone(None, "phone")

    def test_international_phone_format(self):
        """Test international phone number format."""
        result = validators.validate_phone("+44 20 7946 0958", "phone")
        assert isinstance(result, str)

    def test_phone_with_parentheses(self):
        """Test phone with parentheses."""
        result = validators.validate_phone("(555) 123-4567", "phone")
        assert isinstance(result, str)


class TestValidateEmail:
    """Tests for validate_email."""

    def test_accepts_valid_email(self):
        """Test that valid emails are accepted."""
        result = validators.validate_email("test@example.com", "email")
        assert result.lower() == "test@example.com"

    def test_normalizes_email_to_lowercase(self):
        """Test that email is normalized to lowercase."""
        result = validators.validate_email("Test@Example.COM", "email")
        assert result == "test@example.com"

    def test_raises_on_empty_email(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="email must be a non-empty string"):
            validators.validate_email("", "email")

    def test_raises_on_invalid_email(self):
        """Test that invalid email raises ValueError."""
        with pytest.raises(ValueError, match="email must be a valid email"):
            validators.validate_email("not-an-email", "email")

    def test_raises_on_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="email must be a non-empty string"):
            validators.validate_email(None, "email")

    def test_email_with_subdomain(self):
        """Test email with subdomain."""
        result = validators.validate_email("test@mail.example.com", "email")
        assert result == "test@mail.example.com"

    def test_email_with_plus_addressing(self):
        """Test email with plus addressing."""
        result = validators.validate_email("test+tag@example.com", "email")
        assert result == "test+tag@example.com"


class TestValidateCountryCode:
    """Tests for validate_country_code."""

    def test_accepts_valid_two_letter_code(self):
        """Test that valid two-letter country codes are accepted."""
        result = validators.validate_country_code("US", "country_code")
        assert result == "US"

    def test_accepts_lowercase_code(self):
        """Test that lowercase codes are accepted and normalized."""
        result = validators.validate_country_code("us", "country_code")
        assert result == "US"

    def test_normalizes_to_uppercase(self):
        """Test that country code is normalized to uppercase."""
        result = validators.validate_country_code("uK", "country_code")
        assert result == "UK"

    def test_raises_on_empty_code(self):
        """Test that empty code raises ValueError."""
        with pytest.raises(ValueError, match="country_code must be a 2-letter ISO code"):
            validators.validate_country_code("", "country_code")

    def test_raises_on_single_character_code(self):
        """Test that single-character codes raise ValueError."""
        with pytest.raises(ValueError, match="country_code must be a 2-letter ISO code"):
            validators.validate_country_code("U", "country_code")

    def test_raises_on_three_letter_code(self):
        """Test that three-letter codes are rejected."""
        with pytest.raises(ValueError, match="country_code must be a 2-letter ISO code"):
            validators.validate_country_code("USA", "country_code")

    def test_common_country_codes(self):
        """Test various common country codes."""
        codes = ["DE", "FR", "GB", "JP", "CA", "AU"]
        for code in codes:
            result = validators.validate_country_code(code, "country")
            assert result == code


class TestValidatePositiveInt:
    """Tests for validate_positive_int."""

    def test_accepts_positive_integer(self):
        """Test that positive integers are accepted."""
        validators.validate_positive_int(42, "count")  # Should not raise

    def test_accepts_one(self):
        """Test that 1 is accepted."""
        validators.validate_positive_int(1, "count")  # Should not raise

    def test_raises_on_zero(self):
        """Test that zero raises ValueError."""
        with pytest.raises(ValueError, match="count must be a positive integer"):
            validators.validate_positive_int(0, "count")

    def test_raises_on_negative(self):
        """Test that negative integers raise ValueError."""
        with pytest.raises(ValueError, match="count must be a positive integer"):
            validators.validate_positive_int(-5, "count")

    def test_raises_on_float(self):
        """Test that floats are rejected."""
        with pytest.raises(ValueError, match="count must be a positive integer"):
            validators.validate_positive_int(3.14, "count")

    def test_raises_on_string(self):
        """Test that strings raise ValueError."""
        with pytest.raises(ValueError, match="count must be a positive integer"):
            validators.validate_positive_int("42", "count")


class TestValidateNonNegativeInt:
    """Tests for validate_non_negative_int."""

    def test_accepts_zero(self):
        """Test that zero is accepted."""
        validators.validate_non_negative_int(0, "count")  # Should not raise

    def test_accepts_positive_integer(self):
        """Test that positive integers are accepted."""
        validators.validate_non_negative_int(42, "count")  # Should not raise

    def test_raises_on_negative(self):
        """Test that negative integers raise ValueError."""
        with pytest.raises(ValueError, match="count must be a non-negative integer"):
            validators.validate_non_negative_int(-1, "count")

    def test_raises_on_float(self):
        """Test that floats are rejected."""
        with pytest.raises(ValueError, match="count must be a non-negative integer"):
            validators.validate_non_negative_int(0.5, "count")


class TestValidateListOfInstances:
    """Tests for validate_list_of_instances."""

    def test_accepts_valid_list_of_instances(self):
        """Test that valid list of instances is accepted."""
        test_list = [1, 2, 3, 4, 5]
        validators.validate_list_of_instances(test_list, int, "numbers")  # Should not raise

    def test_accepts_empty_list_when_allow_empty_true(self):
        """Test that empty list is accepted when allow_empty=True."""
        validators.validate_list_of_instances(
            [], int, "numbers", allow_empty=True
        )  # Should not raise

    def test_raises_on_empty_list_by_default(self):
        """Test that empty list raises ValueError by default."""
        with pytest.raises(ValueError, match="numbers cannot be empty"):
            validators.validate_list_of_instances([], int, "numbers")

    def test_raises_on_non_list(self):
        """Test that non-list raises ValueError."""
        with pytest.raises(ValueError, match="numbers must be a list"):
            validators.validate_list_of_instances(123, int, "numbers")

    def test_raises_on_string(self):
        """Test that string (which is technically iterable) raises ValueError."""
        with pytest.raises(ValueError, match="numbers must be a list"):
            validators.validate_list_of_instances("123", int, "numbers")

    def test_raises_on_none(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="numbers must be a list"):
            validators.validate_list_of_instances(None, int, "numbers")

    def test_raises_on_wrong_item_type(self):
        """Test that list with wrong item types raises ValueError."""
        with pytest.raises(ValueError, match="numbers must contain only instances of int"):
            validators.validate_list_of_instances([1, 2, "three", 4], int, "numbers")

    def test_raises_on_all_wrong_types(self):
        """Test that list with all wrong types raises ValueError."""
        with pytest.raises(ValueError, match="items must contain only instances of str"):
            validators.validate_list_of_instances([1, 2, 3], str, "items")

    def test_accepts_list_of_strings(self):
        """Test that list of strings is accepted."""
        test_list = ["apple", "banana", "cherry"]
        validators.validate_list_of_instances(test_list, str, "fruits")  # Should not raise

    def test_single_item_list_valid(self):
        """Test that single item list is valid."""
        validators.validate_list_of_instances([42], int, "numbers")  # Should not raise


class TestSetStrippedString:
    """Tests for set_stripped_string."""

    def test_sets_stripped_string(self):
        """Test that string is properly stripped and set."""

        class TestObj:
            field: str = ""

        obj = TestObj()
        validators.set_stripped_string(obj, "field", "  hello world  ")
        assert obj.field == "hello world"

    def test_strips_leading_whitespace(self):
        """Test that leading whitespace is stripped."""

        class TestObj:
            field: str = ""

        obj = TestObj()
        validators.set_stripped_string(obj, "field", "  test")
        assert obj.field == "test"

    def test_strips_trailing_whitespace(self):
        """Test that trailing whitespace is stripped."""

        class TestObj:
            field: str = ""

        obj = TestObj()
        validators.set_stripped_string(obj, "field", "test  ")
        assert obj.field == "test"

    def test_strips_both_ends(self):
        """Test that whitespace is stripped from both ends."""

        class TestObj:
            field: str = ""

        obj = TestObj()
        validators.set_stripped_string(obj, "field", "  test  ")
        assert obj.field == "test"

    def test_preserves_internal_whitespace(self):
        """Test that internal whitespace is preserved."""

        class TestObj:
            field: str = ""

        obj = TestObj()
        validators.set_stripped_string(obj, "field", "  hello  world  ")
        assert obj.field == "hello  world"

    def test_empty_string_after_strip(self):
        """Test that empty string results after stripping whitespace."""

        class TestObj:
            field: str = ""

        obj = TestObj()
        validators.set_stripped_string(obj, "field", "    ")
        assert obj.field == ""

    def test_sets_on_frozen_dataclass(self):
        """Test that set_stripped_string works on frozen dataclasses."""
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class TestObj:
            field: str

        obj = TestObj(field="original")
        validators.set_stripped_string(obj, "field", "  updated  ")
        assert obj.field == "updated"


class TestSetNormalizedString:
    """Tests for set_normalized_string."""

    def test_sets_stripped_string_with_no_transform(self):
        """Test that string is stripped with no transform."""

        class MockObj:
            field = "original"

        obj = MockObj()
        validators.set_normalized_string(obj, "field", "  hello  ", "none")

        assert obj.field == "hello"

    def test_sets_uppercase_with_upper_transform(self):
        """Test that string is uppercased with upper transform."""

        class MockObj:
            field = "original"

        obj = MockObj()
        validators.set_normalized_string(obj, "field", "  hello  ", "upper")

        assert obj.field == "HELLO"

    def test_sets_lowercase_with_lower_transform(self):
        """Test that string is lowercased with lower transform."""

        class MockObj:
            field = "original"

        obj = MockObj()
        validators.set_normalized_string(obj, "field", "  HELLO  ", "lower")

        assert obj.field == "hello"

    def test_default_transform_is_none(self):
        """Test that default transform is 'none'."""

        class MockObj:
            field = "original"

        obj = MockObj()
        validators.set_normalized_string(obj, "field", "  MiXeD  ")

        assert obj.field == "MiXeD"

    def test_strips_whitespace_with_mixed_case(self):
        """Test that whitespace is stripped with mixed case."""

        class MockObj:
            field = "original"

        obj = MockObj()
        validators.set_normalized_string(obj, "field", "   MiXeD CaSe   ", "none")

        assert obj.field == "MiXeD CaSe"

    def test_preserves_internal_whitespace(self):
        """Test that internal whitespace is preserved."""

        class MockObj:
            field = "original"

        obj = MockObj()
        validators.set_normalized_string(obj, "field", "  hello world  ", "upper")

        assert obj.field == "HELLO WORLD"

    def test_handles_empty_after_strip(self):
        """Test that empty string after strip is handled."""

        class MockObj:
            field = "original"

        obj = MockObj()
        validators.set_normalized_string(obj, "field", "   ", "none")

        assert obj.field == ""
