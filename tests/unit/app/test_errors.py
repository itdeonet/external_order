"""Unit tests for the errors module."""

from traceback import TracebackException

import pytest

from src.app.errors import (
    ArtworkError,
    BaseError,
    ErrorQueue,
    InsdesError,
    NotifyError,
    SaleError,
)


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

        assert str(exc) == "Something went wrong (Order ID: ORD-12345)"

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

        assert str(exc) == " (Order ID: ORD-123)"

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = BaseError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Error (Order ID: 12345)"

    def test_with_special_characters_in_message(self):
        """Test with special characters in message."""
        message = "Error: Invalid <data> & 'test'"
        exc = BaseError(message, order_id="ORD-123")

        assert message in str(exc)
        assert "(Order ID: ORD-123)" in str(exc)

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

        assert str(exc) == "Artwork retrieval failed (Order ID: ORD-12345)"

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

        assert str(exc) == " (Order ID: ORD-123)"

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = ArtworkError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Error (Order ID: 12345)"

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

        assert str(exc) == "Provider notify failed (Order ID: ORD-12345)"

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

        assert str(exc) == " (Order ID: ORD-123)"

    def test_with_numeric_order_id(self):
        """Test with numeric order_id."""
        exc = NotifyError("Error", order_id="12345")

        assert exc.order_id == "12345"
        assert str(exc) == "Error (Order ID: 12345)"

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


class TestErrorQueueImmutability:
    """Tests for ErrorQueue immutability (frozen=True)."""

    def test_error_queue_is_frozen(self):
        """Test that ErrorQueue is frozen and cannot be modified."""
        queue = ErrorQueue()

        with pytest.raises(Exception):  # FrozenInstanceError
            queue.new_attribute = "test"

    def test_queue_field_cannot_be_modified(self):
        """Test that _queue field cannot be reassigned."""
        queue = ErrorQueue()

        with pytest.raises(Exception):  # FrozenInstanceError
            queue._queue = None

    def test_frozen_dataclass_instance_equality(self):
        """Test frozen dataclass equality."""
        queue1 = ErrorQueue()
        queue2 = ErrorQueue()

        # Different instances even if they're both empty
        assert queue1 is not queue2


class TestAllCustomErrorsInQueue:
    """Tests for all custom error types in ErrorQueue."""

    def test_base_error_in_queue(self):
        """Test collecting BaseError in ErrorQueue."""
        queue = ErrorQueue()
        exc = BaseError("Base error", order_id="ORD-001")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1
        assert "BaseError" in str(errors[0].exc_type)

    def test_artwork_error_in_queue(self):
        """Test collecting ArtworkError in ErrorQueue."""
        queue = ErrorQueue()
        exc = ArtworkError("Artwork error", order_id="ORD-001")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1
        assert "ArtworkError" in str(errors[0].exc_type)

    def test_insdes_error_in_error_queue(self):
        """Test collecting InsdesError in ErrorQueue."""
        queue = ErrorQueue()
        exc = InsdesError("Insdes error", order_id="ORD-002")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1
        assert "InsdesError" in str(errors[0].exc_type)

    def test_notify_error_in_queue(self):
        """Test collecting NotifyError in ErrorQueue."""
        queue = ErrorQueue()
        exc = NotifyError("Notify error", order_id="ORD-003")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1
        assert "NotifyError" in str(errors[0].exc_type)

    def test_sale_error_in_queue(self):
        """Test collecting SaleError in ErrorQueue."""
        queue = ErrorQueue()
        exc = SaleError("Sale error", order_id="ORD-004")

        queue.put(exc)
        errors = queue.all()

        assert len(errors) == 1
        assert "SaleError" in str(errors[0].exc_type)

    def test_all_custom_errors_mixed_in_queue(self):
        """Test collecting all custom error types together."""
        queue = ErrorQueue()
        queue.put(BaseError("Base", order_id="ORD-001"))
        queue.put(ArtworkError("Artwork", order_id="ORD-002"))
        queue.put(InsdesError("Insdes", order_id="ORD-003"))
        queue.put(NotifyError("Notify", order_id="ORD-004"))
        queue.put(SaleError("Sale", order_id="ORD-005"))

        errors = queue.all()
        assert len(errors) == 5

        type_strings = [str(e.exc_type.__name__) for e in errors]
        assert "BaseError" in type_strings
        assert "ArtworkError" in type_strings
        assert "InsdesError" in type_strings
        assert "NotifyError" in type_strings
        assert "SaleError" in type_strings

    def test_summarize_with_all_custom_errors(self):
        """Test summarize() with all custom exception types."""
        queue = ErrorQueue()
        queue.put(BaseError("Base error", order_id="ORD-001"))
        queue.put(ArtworkError("Artwork error", order_id="ORD-002"))
        queue.put(InsdesError("Insdes error", order_id="ORD-003"))
        queue.put(NotifyError("Notify error", order_id="ORD-004"))
        queue.put(SaleError("Sale error", order_id="ORD-005"))

        summary = queue.summarize()

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
            expected = f"{message} (Order ID: {order_id})"
            assert str(error) == expected
