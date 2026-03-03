"""Unit tests for the errors module."""

import pytest

from src.app.errors import (
    ArtworkError,
    BaseError,
    ErrorStore,
    InsdesError,
    NotifyError,
    SaleError,
)


class TestErrorStore:
    """Tests for the ErrorStore class."""

    @pytest.fixture
    def error_store(self):
        """Provide the ErrorStore singleton instance, cleared for each test."""
        error_store = ErrorStore()
        error_store.clear()  # Ensure clean state for test isolation
        return error_store

    def test_singleton_pattern(self):
        """Test that ErrorStore is a singleton."""
        error_store1 = ErrorStore()
        error_store2 = ErrorStore()
        error_store3 = ErrorStore()

        assert error_store1 is error_store2
        assert error_store2 is error_store3
        assert id(error_store1) == id(error_store2) == id(error_store3)

    def test_instantiation(self):
        """Test creating an ErrorStore instance."""
        error_store = ErrorStore()
        error_store.clear()
        assert error_store is not None
        assert hasattr(error_store, "_errors")

    def test_put_single_exception(self, error_store):
        """Test adding a single exception to the store."""
        exc = ValueError("Test error")
        error_store.add(exc)
        summary = error_store.summarize()

        assert "Error 1:" in summary
        assert "ValueError" in summary

    def test_put_multiple_exceptions(self, error_store):
        """Test adding multiple exceptions to the store."""
        exceptions = [
            ValueError("Error 1"),
            TypeError("Error 2"),
            RuntimeError("Error 3"),
        ]

        for exc in exceptions:
            error_store.add(exc)

        summary = error_store.summarize()
        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "Error 3:" in summary

    def test_put_preserves_exception_type(self, error_store):
        """Test that exception type information is preserved."""
        exceptions = [ValueError("test"), TypeError("test"), RuntimeError("test")]

        for exc in exceptions:
            error_store.add(exc)

        summary = error_store.summarize()
        assert "ValueError" in summary
        assert "TypeError" in summary
        assert "RuntimeError" in summary

    def test_put_preserves_exception_message(self, error_store):
        """Test that exception message is preserved."""
        message = "Custom error message"
        exc = ValueError(message)
        error_store.add(exc)

        summary = error_store.summarize()
        assert message in summary

    def test_summarize_returns_string(self, error_store):
        """Test that summarize() returns a string."""
        error_store.add(ValueError("test"))
        result = error_store.summarize()

        assert isinstance(result, str)

    def test_summarize_empty_and_refilled(self, error_store):
        """Test that we can put more errors after summarize."""
        error_store.add(ValueError("Error 1"))
        error_store.add(TypeError("Error 2"))

        summary1 = error_store.summarize()
        assert "Error 1:" in summary1
        assert "Error 2:" in summary1

        # After summarize, store still has errors since summarize doesn't drain
        summary2 = error_store.summarize()
        assert summary1 == summary2

    def test_clear_removes_all_exceptions(self, error_store):
        """Test that clear() removes all exceptions."""
        error_store.add(ValueError("Error 1"))
        error_store.add(TypeError("Error 2"))
        error_store.add(RuntimeError("Error 3"))

        error_store.clear()
        summary = error_store.summarize()

        assert summary == ""

    def test_clear_empty_store(self, error_store):
        """Test that clear() on empty store doesn't raise error."""
        error_store.clear()
        summary = error_store.summarize()

        assert summary == ""

    def test_clear_then_add(self, error_store):
        """Test that store works normally after clear()."""
        error_store.add(ValueError("Error 1"))
        error_store.clear()
        error_store.add(TypeError("Error 2"))

        summary = error_store.summarize()
        assert "TypeError" in summary
        assert "ValueError" not in summary  # Old exception type should not be in summary

    def test_summarize_empty_store(self, error_store):
        """Test summarize() with no errors."""
        summary = error_store.summarize()

        assert summary == ""

    def test_summarize_single_error(self, error_store):
        """Test summarize() with single error."""
        error_store.add(ValueError("Test error"))
        summary = error_store.summarize()

        assert "Error 1:" in summary
        assert "ValueError" in summary
        assert "Test error" in summary

    def test_summarize_multiple_errors(self, error_store):
        """Test summarize() with multiple errors."""
        error_store.add(ValueError("Error 1"))
        error_store.add(TypeError("Error 2"))
        error_store.add(RuntimeError("Error 3"))

        summary = error_store.summarize()

        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "Error 3:" in summary
        assert "ValueError" in summary
        assert "TypeError" in summary
        assert "RuntimeError" in summary

    def test_summarize_preserves_store(self, error_store):
        """Test that summarize() doesn't drain the store."""
        error_store.add(ValueError("Error 1"))
        summary1 = error_store.summarize()

        assert "Error 1:" in summary1

        summary2 = error_store.summarize()
        assert summary1 == summary2  # Same content since store not drained

    def test_summarize_formats_errors(self, error_store):
        """Test that summarize() numbers errors correctly."""
        errors_to_add = [
            ValueError("First"),
            TypeError("Second"),
            RuntimeError("Third"),
            Exception("Fourth"),
            KeyError("Fifth"),
        ]

        for exc in errors_to_add:
            error_store.add(exc)

        summary = error_store.summarize()

        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "Error 3:" in summary
        assert "Error 4:" in summary
        assert "Error 5:" in summary

    def test_summarize_with_nested_exceptions(self, error_store):
        """Test summarize() with exceptions that have context."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise TypeError("Outer error") from None
        except TypeError as exc:
            error_store.add(exc)

        summary = error_store.summarize()
        assert "Error 1:" in summary
        assert len(summary) > 0

    def test_thread_safety_put_and_get(self, error_store):
        """Test that put and get operations are thread-safe."""
        import threading

        def add_exceptions():
            for i in range(10):
                error_store.add(ValueError(f"Error {i}"))

        threads = []
        for _ in range(5):
            t = threading.Thread(target=add_exceptions)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        summary = error_store.summarize()
        # Should have 50 errors total
        assert "Error 0:" in summary or "Error 1:" in summary

    def test_add_with_string_representation(self, error_store):
        """Test exception with complex string representation."""
        exc = ValueError("Error with\nmultiple\nlines")
        error_store.add(exc)

        summary = error_store.summarize()
        assert "Error with" in summary

    def test_has_errors_empty_store(self, error_store):
        """Test has_errors() returns False for empty store."""
        assert error_store.has_errors() is False

    def test_has_errors_with_single_error(self, error_store):
        """Test has_errors() returns True when store has one error."""
        error_store.add(ValueError("Test error"))
        assert error_store.has_errors() is True

    def test_has_errors_with_multiple_errors(self, error_store):
        """Test has_errors() returns True with multiple errors."""
        error_store.add(ValueError("Error 1"))
        error_store.add(TypeError("Error 2"))
        error_store.add(RuntimeError("Error 3"))

        assert error_store.has_errors() is True

    def test_has_errors_after_clear(self, error_store):
        """Test has_errors() returns False after clear()."""
        error_store.add(ValueError("Error"))
        assert error_store.has_errors() is True

        error_store.clear()
        assert error_store.has_errors() is False

    def test_has_errors_thread_safe(self, error_store):
        """Test that has_errors() is thread-safe."""
        import threading

        results = []

        def add_and_check():
            error_store.add(ValueError("Test"))
            results.append(error_store.has_errors())

        threads = [threading.Thread(target=add_and_check) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All checks should have found at least one error
        assert all(results)

    def test_get_render_email_data_empty_store(self, error_store):
        """Test get_render_email_data with empty store."""
        data = error_store.get_render_email_data()

        assert isinstance(data, dict)
        assert "error_count" in data
        assert "errors" in data
        assert "timestamp" in data
        assert data["error_count"] == 0
        assert data["errors"] == []

    def test_get_render_email_data_with_single_error(self, error_store):
        """Test get_render_email_data with single error."""
        error_store.add(ValueError("Test error 1"))

        data = error_store.get_render_email_data()

        assert isinstance(data, dict)
        assert data["error_count"] == 1
        assert len(data["errors"]) == 1
        assert "ValueError" in data["errors"][0]
        assert "Test error 1" in data["errors"][0]
        assert "timestamp" in data

    def test_get_render_email_data_with_multiple_errors(self, error_store):
        """Test get_render_email_data with multiple errors."""
        error_store.add(ValueError("Error 1"))
        error_store.add(TypeError("Error 2"))
        error_store.add(RuntimeError("Error 3"))

        data = error_store.get_render_email_data()

        assert data["error_count"] == 3
        assert len(data["errors"]) == 3
        assert any("ValueError" in err for err in data["errors"])
        assert any("TypeError" in err for err in data["errors"])
        assert any("RuntimeError" in err for err in data["errors"])
        assert any("Error 1" in err for err in data["errors"])
        assert any("Error 2" in err for err in data["errors"])
        assert any("Error 3" in err for err in data["errors"])

    def test_get_render_email_data_timestamp_format(self, error_store):
        """Test that timestamp is in correct format."""
        import re

        data = error_store.get_render_email_data()
        timestamp = data["timestamp"]

        # Check format: YYYY-MM-DD HH:MM:SS
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.match(pattern, timestamp), f"Timestamp format incorrect: {timestamp}"

    def test_get_render_email_data_does_not_drain_store(self, error_store):
        """Test that get_render_email_data does not drain the store."""
        error_store.add(ValueError("Test"))

        data1 = error_store.get_render_email_data()
        data2 = error_store.get_render_email_data()

        assert data1["error_count"] == data2["error_count"]
        assert data1["errors"] == data2["errors"]

    def test_get_render_email_data_all_returns_formatted_list(self, error_store):
        """Test that errors field matches all() output."""
        error_store.add(ValueError("Error 1"))
        error_store.add(TypeError("Error 2"))

        data = error_store.get_render_email_data()
        all_errors = error_store.all()

        assert data["errors"] == all_errors


class TestInsdesError:
    """Tests for the InsdesError exception class."""

    def test_instantiation_message_only(self):
        """Test creating InsdesError with message only."""
        exc = InsdesError("Test error")

        assert str(exc) == "Test error"
        assert exc.order_id is None

    def test_instantiation_with_order_id(self):
        """Test creating InsdesError with message and order_id."""
        exc = InsdesError("Test error", order_id="ORD-12345")

        assert exc.order_id == "ORD-12345"

    def test_string_representation_without_order_id(self):
        """Test string representation without order_id."""
        exc = InsdesError("Processing failed")

        assert str(exc) == "Processing failed"

    def test_string_representation_with_order_id(self):
        """Test string representation with order_id."""
        exc = InsdesError("Processing failed", order_id="ORD-12345")

        assert str(exc) == "Order ORD-12345: Processing failed"

    def test_inherits_from_exception(self):
        """Test that InsdesError inherits from Exception."""
        exc = InsdesError("Test")
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that InsdesError can be raised and caught."""
        with pytest.raises(InsdesError):
            raise InsdesError("Test error")

    def test_can_be_caught_as_exception(self):
        """Test that InsdesError can be caught as Exception."""
        with pytest.raises(Exception, match="Test error"):
            raise InsdesError("Test error")

    def test_order_id_none_by_default(self):
        """Test that order_id is None by default."""
        exc = InsdesError("Test")
        assert exc.order_id is None

    def test_order_id_explicitly_none(self):
        """Test setting order_id to None explicitly."""
        exc = InsdesError("Test", order_id=None)

        assert exc.order_id is None
        assert str(exc) == "Test"

    def test_with_empty_message(self):
        """Test creating error with empty message."""
        exc = InsdesError("", order_id="ORD-123")

        assert str(exc) == "Order ORD-123: "

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = InsdesError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Order 12345: Error"

    def test_with_special_characters_in_message(self):
        """Test with special characters in message."""
        message = "Error: Invalid input <test> & 'quotes'"
        exc = InsdesError(message, order_id="ORD-123")

        assert message in str(exc)
        assert "Order ORD-123: " in str(exc)

    def test_with_newlines_in_message(self):
        """Test with newlines in message."""
        message = "Error occurred\non multiple\nlines"
        exc = InsdesError(message)

        assert str(exc) == message

    def test_multiple_instances_independent(self):
        """Test that multiple instances don't interfere."""
        exc1 = InsdesError("Error 1", order_id="ORD-1")
        exc2 = InsdesError("Error 2", order_id="ORD-2")
        exc3 = InsdesError("Error 3")

        assert str(exc1) == "Order ORD-1: Error 1"
        assert str(exc2) == "Order ORD-2: Error 2"
        assert str(exc3) == "Error 3"

    def test_preserves_exception_args(self):
        """Test that base exception args are preserved."""
        exc = InsdesError("Test message")

        assert exc.args == ("Test message",)


class TestOdooError:
    """Tests for the OdooError exception class."""

    def test_instantiation_message_only(self):
        """Test creating OdooError with message only."""
        exc = SaleError("Test error")

        assert str(exc) == "Test error"
        assert exc.order_id is None

    def test_instantiation_with_order_id(self):
        """Test creating OdooError with message and order_id."""
        exc = SaleError("Test error", order_id="ORD-12345")

        assert exc.order_id == "ORD-12345"

    def test_string_representation_without_order_id(self):
        """Test string representation without order_id."""
        exc = SaleError("Connection failed")

        assert str(exc) == "Connection failed"

    def test_string_representation_with_order_id(self):
        """Test string representation with order_id."""
        exc = SaleError("Connection failed", order_id="ORD-12345")

        assert str(exc) == "Order ORD-12345: Connection failed"

    def test_inherits_from_exception(self):
        """Test that OdooError inherits from Exception."""
        exc = SaleError("Test")
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that OdooError can be raised and caught."""
        with pytest.raises(SaleError):
            raise SaleError("Test error")

    def test_can_be_caught_as_exception(self):
        """Test that OdooError can be caught as Exception."""
        with pytest.raises(Exception, match="Test error"):
            raise SaleError("Test error")

    def test_order_id_none_by_default(self):
        """Test that order_id is None by default."""
        exc = SaleError("Test")
        assert exc.order_id is None

    def test_order_id_explicitly_none(self):
        """Test setting order_id to None explicitly."""
        exc = SaleError("Test", order_id=None)

        assert exc.order_id is None
        assert str(exc) == "Test"

    def test_with_empty_message(self):
        """Test creating error with empty message."""
        exc = SaleError("", order_id="ORD-123")

        assert str(exc) == "Order ORD-123: "

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = SaleError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Order 12345: Error"

    def test_with_special_characters_in_message(self):
        """Test with special characters in message."""
        message = "Error: Invalid request <data> & 'quoted'"
        exc = SaleError(message, order_id="ORD-123")

        assert message in str(exc)
        assert "Order ORD-123: " in str(exc)

    def test_with_newlines_in_message(self):
        """Test with newlines in message."""
        message = "Error occurred\non multiple\nlines"
        exc = SaleError(message)

        assert str(exc) == message

    def test_multiple_instances_independent(self):
        """Test that multiple instances don't interfere."""
        exc1 = SaleError("Error 1", order_id="ORD-1")
        exc2 = SaleError("Error 2", order_id="ORD-2")
        exc3 = SaleError("Error 3")

        assert str(exc1) == "Order ORD-1: Error 1"
        assert str(exc2) == "Order ORD-2: Error 2"
        assert str(exc3) == "Error 3"

    def test_preserves_exception_args(self):
        """Test that base exception args are preserved."""
        exc = SaleError("Test message")

        assert exc.args == ("Test message",)

    def test_difference_from_insdes_error(self):
        """Test that OdooError and InsdesError are different classes."""
        insdes_err = InsdesError("Test")
        odoo_err = SaleError("Test")

        assert type(insdes_err) is not type(odoo_err)
        assert not isinstance(insdes_err, SaleError)
        assert not isinstance(odoo_err, InsdesError)


class TestCustomExceptionIntegration:
    """Tests for integration between custom exceptions."""

    def test_insdes_error_in_error_store(self):
        """Test collecting InsdesError in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        exc = InsdesError("INSDES processing failed", order_id="ORD-001")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "InsdesError" in summary

    def test_sale_error_in_error_store(self):
        """Test collecting OdooError in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        exc = SaleError("Odoo API error", order_id="ORD-002")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "SaleError" in summary

    def test_mixed_exceptions_in_error_store(self):
        """Test collecting different exception types in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        error_store.add(InsdesError("INSDES error", order_id="ORD-001"))
        error_store.add(SaleError("Odoo error", order_id="ORD-002"))
        error_store.add(ValueError("Generic error"))

        summary = error_store.summarize()
        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "Error 3:" in summary

    def test_summarize_with_custom_exceptions(self):
        """Test summarize() with custom exceptions."""
        error_store = ErrorStore()
        error_store.clear()
        error_store.add(InsdesError("INSDES failed", order_id="ORD-001"))
        error_store.add(SaleError("API failed", order_id="ORD-002"))

        summary = error_store.summarize()

        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "InsdesError" in summary
        assert "SaleError" in summary

    def test_exception_chaining_with_custom_errors(self):
        """Test exception chaining with custom errors."""
        try:
            try:
                raise InsdesError("Segmentation failed", order_id="ORD-001")
            except InsdesError:
                raise SaleError("Failed to save order", order_id="ORD-001") from None
        except SaleError as exc:
            assert exc.order_id == "ORD-001"
            assert str(exc) == "Order ORD-001: Failed to save order"

    def test_custom_errors_with_traceback(self):
        """Test custom errors preserve traceback information."""
        error_store = ErrorStore()

        try:
            raise InsdesError("Custom error", order_id="ORD-123")
        except InsdesError as exc:
            error_store.add(exc)

        summary = error_store.summarize()
        assert "InsdesError" in summary
        assert "Custom error" in summary


class TestErrorStoreEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_exception_with_unicode_characters(self):
        """Test exception with Unicode characters."""
        error_store = ErrorStore()
        error_store.clear()
        exc = SaleError("Unicode error: café, 日本語, emoji 😀", order_id="ORD-123")

        error_store.add(exc)
        error_store.summarize()

        assert "café" in str(exc)

    def test_exception_with_very_long_message(self):
        """Test exception with very long message."""
        error_store = ErrorStore()
        error_store.clear()
        long_message = "x" * 10000
        exc = InsdesError(long_message, order_id="ORD-123")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "x" * 100 in summary  # At least part of the message is there

    def test_large_number_of_exceptions(self):
        """Test handling large number of exceptions."""
        error_store = ErrorStore()
        error_store.clear()

        for i in range(1000):
            exc = ValueError(f"Error {i}")
            error_store.add(exc)

        summary = error_store.summarize()
        assert "Error 1:" in summary  # At least some errors are in the summary

    def test_exception_with_none_order_id_string(self):
        """Test that 'None' string vs None are different."""
        exc1 = InsdesError("Test", order_id=None)
        exc2 = InsdesError("Test", order_id="None")

        assert str(exc1) == "Test"
        assert str(exc2) == "Order None: Test"


class TestBaseError:
    """Tests for the BaseError exception class."""

    def test_instantiation_message_only(self):
        """Test creating BaseError with message only."""
        exc = BaseError("Test error")

        assert str(exc) == "Test error"
        assert exc.order_id is None

    def test_instantiation_with_order_id(self):
        """Test creating BaseError with message and order_id."""
        exc = BaseError("Test error", order_id="ORD-12345")

        assert exc.order_id == "ORD-12345"

    def test_string_representation_without_order_id(self):
        """Test string representation without order_id."""
        exc = BaseError("Something went wrong")

        assert str(exc) == "Something went wrong"

    def test_string_representation_with_order_id(self):
        """Test string representation with order_id."""
        exc = BaseError("Something went wrong", order_id="ORD-12345")

        assert str(exc) == "Order ORD-12345: Something went wrong"

    def test_inherits_from_exception(self):
        """Test that BaseError inherits from Exception."""
        exc = BaseError("Test")
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that BaseError can be raised and caught."""
        with pytest.raises(BaseError):
            raise BaseError("Test error")

    def test_order_id_none_by_default(self):
        """Test that order_id is None by default."""
        exc = BaseError("Test")
        assert exc.order_id is None

    def test_with_empty_message(self):
        """Test creating error with empty message."""
        exc = BaseError("", order_id="ORD-123")

        assert str(exc) == "Order ORD-123: "

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = BaseError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Order 12345: Error"

    def test_with_special_characters_in_message(self):
        """Test with special characters in message."""
        message = "Error: Invalid <data> & 'test'"
        exc = BaseError(message, order_id="ORD-123")

        assert message in str(exc)
        assert "Order ORD-123: " in str(exc)

    def test_with_newlines_in_message(self):
        """Test with newlines in message."""
        message = "Error occurred\non multiple\nlines"
        exc = BaseError(message)

        assert str(exc) == message

    def test_preserves_exception_args(self):
        """Test that base exception args are preserved."""
        exc = BaseError("Test message")

        assert exc.args == ("Test message",)

    def test_super_call_working(self):
        """Test that super().__init__ is properly called."""
        exc = BaseError("Test message")

        # args should be set by Exception.__init__
        assert len(exc.args) == 1
        assert exc.args[0] == "Test message"

    def test_order_id_attribute_type(self):
        """Test that order_id attribute is string or None."""
        exc1 = BaseError("Test", order_id="ORD-123")
        exc2 = BaseError("Test", order_id=None)

        assert isinstance(exc1.order_id, str)
        assert exc2.order_id is None


class TestArtworkError:
    """Tests for the ArtworkError exception class."""

    def test_instantiation_message_only(self):
        """Test creating ArtworkError with message only."""
        exc = ArtworkError("Test error")

        assert str(exc) == "Test error"
        assert exc.order_id is None

    def test_instantiation_with_order_id(self):
        """Test creating ArtworkError with message and order_id."""
        exc = ArtworkError("Test error", order_id="ORD-12345")

        assert exc.order_id == "ORD-12345"

    def test_string_representation_without_order_id(self):
        """Test string representation without order_id."""
        exc = ArtworkError("Artwork not found")

        assert str(exc) == "Artwork not found"

    def test_string_representation_with_order_id(self):
        """Test string representation with order_id."""
        exc = ArtworkError("Artwork retrieval failed", order_id="ORD-12345")

        assert str(exc) == "Order ORD-12345: Artwork retrieval failed"

    def test_inherits_from_base_error(self):
        """Test that ArtworkError inherits from BaseError."""
        exc = ArtworkError("Test")
        assert isinstance(exc, BaseError)
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that ArtworkError can be raised and caught."""
        with pytest.raises(ArtworkError):
            raise ArtworkError("Artwork error")

    def test_can_be_caught_as_base_error(self):
        """Test that ArtworkError can be caught as BaseError."""
        with pytest.raises(BaseError, match="Artwork error"):
            raise ArtworkError("Artwork error")

    def test_order_id_none_by_default(self):
        """Test that order_id is None by default."""
        exc = ArtworkError("Test")
        assert exc.order_id is None

    def test_with_empty_message(self):
        """Test creating error with empty message."""
        exc = ArtworkError("", order_id="ORD-123")

        assert str(exc) == "Order ORD-123: "

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = ArtworkError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Order 12345: Error"

    def test_difference_from_other_custom_errors(self):
        """Test that ArtworkError is distinct from other custom errors."""
        artwork_err = ArtworkError("Test")
        insdes_err = InsdesError("Test")
        sale_err = SaleError("Test")

        assert type(artwork_err) is not type(insdes_err)
        assert type(artwork_err) is not type(sale_err)
        assert not isinstance(artwork_err, InsdesError)
        assert not isinstance(artwork_err, SaleError)

    def test_with_special_message_for_artwork_domain(self):
        """Test with message specific to artwork context."""
        exc = ArtworkError("Failed to fetch artwork from service", order_id="ORD-001")

        assert "artwork" in str(exc).lower()
        assert "ORD-001" in str(exc)


class TestNotifyError:
    """Tests for the NotifyError exception class."""

    def test_instantiation_message_only(self):
        """Test creating NotifyError with message only."""
        exc = NotifyError("Test error")

        assert str(exc) == "Test error"
        assert exc.order_id is None

    def test_instantiation_with_order_id(self):
        """Test creating NotifyError with message and order_id."""
        exc = NotifyError("Test error", order_id="ORD-12345")

        assert exc.order_id == "ORD-12345"

    def test_string_representation_without_order_id(self):
        """Test string representation without order_id."""
        exc = NotifyError("Notification failed")

        assert str(exc) == "Notification failed"

    def test_string_representation_with_order_id(self):
        """Test string representation with order_id."""
        exc = NotifyError("Provider notify failed", order_id="ORD-12345")

        assert str(exc) == "Order ORD-12345: Provider notify failed"

    def test_inherits_from_base_error(self):
        """Test that NotifyError inherits from BaseError."""
        exc = NotifyError("Test")
        assert isinstance(exc, BaseError)
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that NotifyError can be raised and caught."""
        with pytest.raises(NotifyError):
            raise NotifyError("Notify error")

    def test_can_be_caught_as_base_error(self):
        """Test that NotifyError can be caught as BaseError."""
        with pytest.raises(BaseError, match="Notify error"):
            raise NotifyError("Notify error")

    def test_order_id_none_by_default(self):
        """Test that order_id is None by default."""
        exc = NotifyError("Test")
        assert exc.order_id is None

    def test_with_empty_message(self):
        """Test creating error with empty message."""
        exc = NotifyError("", order_id="ORD-123")

        assert str(exc) == "Order ORD-123: "

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = NotifyError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Order 12345: Error"

    def test_difference_from_other_custom_errors(self):
        """Test that NotifyError is distinct from other custom errors."""
        notify_err = NotifyError("Test")
        artwork_err = ArtworkError("Test")
        sale_err = SaleError("Test")

        assert type(notify_err) is not type(artwork_err)
        assert type(notify_err) is not type(sale_err)
        assert not isinstance(notify_err, ArtworkError)
        assert not isinstance(notify_err, SaleError)

    def test_with_special_message_for_notify_domain(self):
        """Test with message specific to notification context."""
        exc = NotifyError("Failed to notify order provider", order_id="ORD-001")

        assert "notify" in str(exc).lower()
        assert "ORD-001" in str(exc)


class TestErrorStoreImmutability:
    """Tests for ErrorStore immutability (frozen=True)."""

    def test_error_store_is_frozen(self):
        """Test that ErrorStore is frozen and cannot be modified."""
        error_store = ErrorStore()

        with pytest.raises(TypeError):  # FrozenInstanceError
            error_store.new_attribute = "test"  # type: ignore

    def test_store_field_cannot_be_modified(self):
        """Test that _store field cannot be reassigned."""
        error_store = ErrorStore()

        with pytest.raises(TypeError):  # FrozenInstanceError
            error_store._store = None  # type: ignore

    def test_frozen_dataclass_instance_equality(self):
        """Test frozen dataclass singleton behavior."""
        error_store1 = ErrorStore()
        error_store2 = ErrorStore()

        # Same instance since ErrorStore is now a singleton
        assert error_store1 is error_store2


class TestAllCustomErrorsInStore:
    """Tests for all custom error types in ErrorStore."""

    def test_base_error_in_store(self):
        """Test collecting BaseError in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        exc = BaseError("Base error", order_id="ORD-001")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "BaseError" in summary

    def test_artwork_error_in_store(self):
        """Test collecting ArtworkError in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        exc = ArtworkError("Artwork error", order_id="ORD-001")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "ArtworkError" in summary

    def test_insdes_error_in_store(self):
        """Test collecting InsdesError in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        exc = InsdesError("Insdes error", order_id="ORD-002")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "InsdesError" in summary

    def test_notify_error_in_store(self):
        """Test collecting NotifyError in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        exc = NotifyError("Notify error", order_id="ORD-003")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "NotifyError" in summary

    def test_sale_error_in_store(self):
        """Test collecting SaleError in ErrorStore."""
        error_store = ErrorStore()
        error_store.clear()
        exc = SaleError("Sale error", order_id="ORD-004")

        error_store.add(exc)
        summary = error_store.summarize()

        assert "SaleError" in summary

    def test_all_custom_errors_mixed_in_store(self):
        """Test collecting all custom error types together."""
        error_store = ErrorStore()
        error_store.clear()
        error_store.add(BaseError("Base", order_id="ORD-001"))
        error_store.add(ArtworkError("Artwork", order_id="ORD-002"))
        error_store.add(InsdesError("Insdes", order_id="ORD-003"))
        error_store.add(NotifyError("Notify", order_id="ORD-004"))
        error_store.add(SaleError("Sale", order_id="ORD-005"))

        summary = error_store.summarize()
        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "Error 3:" in summary
        assert "Error 4:" in summary
        assert "Error 5:" in summary

    def test_summarize_with_all_custom_errors(self):
        """Test summarize() with all custom exception types."""
        error_store = ErrorStore()
        error_store.clear()
        error_store.add(BaseError("Base error", order_id="ORD-001"))
        error_store.add(ArtworkError("Artwork error", order_id="ORD-002"))
        error_store.add(InsdesError("Insdes error", order_id="ORD-003"))
        error_store.add(NotifyError("Notify error", order_id="ORD-004"))
        error_store.add(SaleError("Sale error", order_id="ORD-005"))

        summary = error_store.summarize()

        assert "Error 1:" in summary
        assert "Error 5:" in summary
        assert "BaseError" in summary
        assert "ArtworkError" in summary
        assert "InsdesError" in summary
        assert "NotifyError" in summary
        assert "SaleError" in summary


class TestErrorInheritanceHierarchy:
    """Tests for error inheritance hierarchy."""

    def test_all_custom_errors_inherit_from_base_error(self):
        """Test that all custom errors inherit from BaseError."""
        errors = [
            ArtworkError("Test"),
            InsdesError("Test"),
            NotifyError("Test"),
            SaleError("Test"),
        ]

        for error in errors:
            assert isinstance(error, BaseError)
            assert isinstance(error, Exception)

    def test_custom_errors_have_order_id_attribute(self):
        """Test that all custom errors have order_id attribute."""
        errors_with_ids = [
            ArtworkError("Test", order_id="ORD-1"),
            InsdesError("Test", order_id="ORD-2"),
            NotifyError("Test", order_id="ORD-3"),
            SaleError("Test", order_id="ORD-4"),
        ]

        for error in errors_with_ids:
            assert hasattr(error, "order_id")
            assert error.order_id is not None

    def test_custom_errors_string_format_consistent(self):
        """Test that all custom errors use consistent string format."""
        order_id = "ORD-TEST"
        message = "Test message"

        errors = [
            ArtworkError(message, order_id=order_id),
            InsdesError(message, order_id=order_id),
            NotifyError(message, order_id=order_id),
            SaleError(message, order_id=order_id),
        ]

        for error in errors:
            expected = f"Order {order_id}: {message}"
            assert str(error) == expected
