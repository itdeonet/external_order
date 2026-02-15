"""Unit tests for the errors module."""

from traceback import TracebackException

import pytest

from src.app.errors import ErrorQueue, InsdesError, SaleError


class TestErrorQueue:
    """Tests for the ErrorQueue class."""

    @pytest.fixture
    def error_queue(self):
        """Provide a fresh ErrorQueue instance for each test."""
        return ErrorQueue()

    def test_instantiation(self):
        """Test creating an ErrorQueue instance."""
        queue = ErrorQueue()
        assert queue is not None
        assert hasattr(queue, "_queue")

    def test_put_single_exception(self, error_queue):
        """Test adding a single exception to the queue."""
        exc = ValueError("Test error")
        error_queue.put(exc)
        errors = error_queue.all()

        assert len(errors) == 1
        assert isinstance(errors[0], TracebackException)

    def test_put_multiple_exceptions(self, error_queue):
        """Test adding multiple exceptions to the queue."""
        exceptions = [
            ValueError("Error 1"),
            TypeError("Error 2"),
            RuntimeError("Error 3"),
        ]

        for exc in exceptions:
            error_queue.put(exc)

        errors = error_queue.all()
        assert len(errors) == 3

    def test_put_preserves_exception_type(self, error_queue):
        """Test that exception type information is preserved."""
        exceptions = [ValueError("test"), TypeError("test"), RuntimeError("test")]

        for exc in exceptions:
            error_queue.put(exc)

        errors = error_queue.all()
        error_strings = [str(e.exc_type.__name__) for e in errors]

        assert "ValueError" in error_strings
        assert "TypeError" in error_strings
        assert "RuntimeError" in error_strings

    def test_put_preserves_exception_message(self, error_queue):
        """Test that exception message is preserved."""
        message = "Custom error message"
        exc = ValueError(message)
        error_queue.put(exc)

        errors = error_queue.all()
        assert message in "".join(errors[0].format())

    def test_all_returns_list(self, error_queue):
        """Test that all() returns a list."""
        error_queue.put(ValueError("test"))
        result = error_queue.all()

        assert isinstance(result, list)

    def test_all_drains_queue(self, error_queue):
        """Test that all() drains the queue."""
        error_queue.put(ValueError("Error 1"))
        error_queue.put(TypeError("Error 2"))

        errors1 = error_queue.all()
        assert len(errors1) == 2

        errors2 = error_queue.all()
        assert len(errors2) == 0

    def test_all_empty_queue_returns_empty_list(self, error_queue):
        """Test that all() returns empty list when queue is empty."""
        errors = error_queue.all()
        assert errors == []

    def test_clear_removes_all_exceptions(self, error_queue):
        """Test that clear() removes all exceptions."""
        error_queue.put(ValueError("Error 1"))
        error_queue.put(TypeError("Error 2"))
        error_queue.put(RuntimeError("Error 3"))

        error_queue.clear()
        errors = error_queue.all()

        assert len(errors) == 0

    def test_clear_empty_queue(self, error_queue):
        """Test that clear() on empty queue doesn't raise error."""
        error_queue.clear()
        errors = error_queue.all()

        assert len(errors) == 0

    def test_clear_then_put(self, error_queue):
        """Test that queue works normally after clear()."""
        error_queue.put(ValueError("Error 1"))
        error_queue.clear()
        error_queue.put(TypeError("Error 2"))

        errors = error_queue.all()
        assert len(errors) == 1
        assert "TypeError" in str(errors[0].exc_type)

    def test_summarize_empty_queue(self, error_queue):
        """Test summarize() with no errors."""
        summary = error_queue.summarize()

        assert summary == "No errors collected."

    def test_summarize_single_error(self, error_queue):
        """Test summarize() with single error."""
        error_queue.put(ValueError("Test error"))
        summary = error_queue.summarize()

        assert "Error 1:" in summary
        assert "ValueError" in summary
        assert "Test error" in summary

    def test_summarize_multiple_errors(self, error_queue):
        """Test summarize() with multiple errors."""
        error_queue.put(ValueError("Error 1"))
        error_queue.put(TypeError("Error 2"))
        error_queue.put(RuntimeError("Error 3"))

        summary = error_queue.summarize()

        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "Error 3:" in summary
        assert "ValueError" in summary
        assert "TypeError" in summary
        assert "RuntimeError" in summary

    def test_summarize_drains_queue(self, error_queue):
        """Test that summarize() drains the queue."""
        error_queue.put(ValueError("Error 1"))
        summary = error_queue.summarize()

        assert "Error 1:" in summary

        errors = error_queue.all()
        assert len(errors) == 0

    def test_summarize_error_numbering(self, error_queue):
        """Test that summarize() numbers errors correctly."""
        errors_to_add = [
            ValueError("First"),
            TypeError("Second"),
            RuntimeError("Third"),
            Exception("Fourth"),
            KeyError("Fifth"),
        ]

        for exc in errors_to_add:
            error_queue.put(exc)

        summary = error_queue.summarize()

        assert "Error 1:" in summary
        assert "Error 2:" in summary
        assert "Error 3:" in summary
        assert "Error 4:" in summary
        assert "Error 5:" in summary

    def test_summarize_with_nested_exceptions(self, error_queue):
        """Test summarize() with exceptions that have context."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise TypeError("Outer error") from None
        except TypeError as exc:
            error_queue.put(exc)

        summary = error_queue.summarize()
        assert "Error 1:" in summary
        assert len(summary) > 0

    def test_thread_safety_put_and_get(self, error_queue):
        """Test that put and get operations are thread-safe."""
        import threading

        results = []

        def add_exceptions():
            for i in range(10):
                error_queue.put(ValueError(f"Error {i}"))

        def retrieve_exceptions():
            errors = error_queue.all()
            results.append(len(errors))

        threads = []
        for _ in range(5):
            t = threading.Thread(target=add_exceptions)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        errors = error_queue.all()
        assert len(errors) == 50

    def test_put_with_string_representation(self, error_queue):
        """Test exception with complex string representation."""
        exc = ValueError("Error with\nmultiple\nlines")
        error_queue.put(exc)

        errors = error_queue.all()
        formatted = "".join(errors[0].format())
        assert "Error with" in formatted


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

        assert str(exc) == "Processing failed (Order ID: ORD-12345)"

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

        assert str(exc) == " (Order ID: ORD-123)"

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = InsdesError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Error (Order ID: 12345)"

    def test_with_special_characters_in_message(self):
        """Test with special characters in message."""
        message = "Error: Invalid input <test> & 'quotes'"
        exc = InsdesError(message, order_id="ORD-123")

        assert message in str(exc)
        assert "(Order ID: ORD-123)" in str(exc)

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

        assert str(exc1) == "Error 1 (Order ID: ORD-1)"
        assert str(exc2) == "Error 2 (Order ID: ORD-2)"
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

        assert str(exc) == "Connection failed (Order ID: ORD-12345)"

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

        assert str(exc) == " (Order ID: ORD-123)"

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = SaleError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Error (Order ID: 12345)"

    def test_with_special_characters_in_message(self):
        """Test with special characters in message."""
        message = "Error: Invalid request <data> & 'quoted'"
        exc = SaleError(message, order_id="ORD-123")

        assert message in str(exc)
        assert "(Order ID: ORD-123)" in str(exc)

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

        assert str(exc1) == "Error 1 (Order ID: ORD-1)"
        assert str(exc2) == "Error 2 (Order ID: ORD-2)"
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

    def test_insdes_error_in_error_queue(self):
        """Test collecting InsdesError in ErrorQueue."""
        queue = ErrorQueue()
        exc = InsdesError("INSDES processing failed", order_id="ORD-001")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1
        assert "InsdesError" in str(errors[0].exc_type)

    def test_sale_error_in_error_queue(self):
        """Test collecting OdooError in ErrorQueue."""
        queue = ErrorQueue()
        exc = SaleError("Odoo API error", order_id="ORD-002")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1
        assert "SaleError" in str(errors[0].exc_type)

    def test_mixed_exceptions_in_error_queue(self):
        """Test collecting different exception types in ErrorQueue."""
        queue = ErrorQueue()
        queue.put(InsdesError("INSDES error", order_id="ORD-001"))
        queue.put(SaleError("Odoo error", order_id="ORD-002"))
        queue.put(ValueError("Generic error"))

        errors = queue.all()
        assert len(errors) == 3

    def test_summarize_with_custom_exceptions(self):
        """Test summarize() with custom exceptions."""
        queue = ErrorQueue()
        queue.put(InsdesError("INSDES failed", order_id="ORD-001"))
        queue.put(SaleError("API failed", order_id="ORD-002"))

        summary = queue.summarize()

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
            assert str(exc) == "Failed to save order (Order ID: ORD-001)"

    def test_custom_errors_with_traceback(self):
        """Test custom errors preserve traceback information."""
        queue = ErrorQueue()

        try:
            raise InsdesError("Custom error", order_id="ORD-123")
        except InsdesError as exc:
            queue.put(exc)

        errors = queue.all()
        formatted = "".join(errors[0].format())

        assert "InsdesError" in formatted
        assert "Custom error" in formatted


class TestErrorQueueEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_exception_with_unicode_characters(self):
        """Test exception with Unicode characters."""
        queue = ErrorQueue()
        exc = SaleError("Unicode error: café, 日本語, emoji 😀", order_id="ORD-123")

        queue.put(exc)
        queue.all()
        queue.summarize()

        assert "café" in str(exc)

    def test_exception_with_very_long_message(self):
        """Test exception with very long message."""
        queue = ErrorQueue()
        long_message = "x" * 10000
        exc = InsdesError(long_message, order_id="ORD-123")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1

    def test_large_number_of_exceptions(self):
        """Test handling large number of exceptions."""
        queue = ErrorQueue()

        for i in range(1000):
            exc = ValueError(f"Error {i}")
            queue.put(exc)

        errors = queue.all()
        assert len(errors) == 1000

    def test_exception_with_none_order_id_string(self):
        """Test that 'None' string vs None are different."""
        exc1 = InsdesError("Test", order_id=None)
        exc2 = InsdesError("Test", order_id="None")

        assert str(exc1) == "Test"
        assert str(exc2) == "Test (Order ID: None)"
