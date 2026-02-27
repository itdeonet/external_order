"""Tests for CompletedUseCase."""

from unittest.mock import MagicMock

import pytest

from src.app.completed_sale_use_case import CompletedSaleUseCase
from src.app.errors import SaleError
from src.domain.order import Order, OrderStatus


@pytest.fixture
def mock_order_services():
    """Create a mock registry for order services."""
    mock_registry = MagicMock()
    return mock_registry


@pytest.fixture
def mock_sales_service():
    """Create a mock sales service."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def mock_error_queue():
    """Create a mock error queue."""
    mock_queue = MagicMock()
    return mock_queue


@pytest.fixture
def mock_order():
    """Create a mock order."""
    return MagicMock(spec=Order)


@pytest.fixture
def completed_use_case(mock_order_services, mock_sales_service, mock_error_queue):
    """Create a CompletedUseCase instance with mocked dependencies."""
    return CompletedSaleUseCase(
        order_services=mock_order_services,
        sale_service=mock_sales_service,
        error_queue=mock_error_queue,
    )


class TestCompletedUseCaseInit:
    """Tests for CompletedUseCase initialization."""

    def test_initialization_with_valid_dependencies(
        self, mock_order_services, mock_sales_service, mock_error_queue
    ):
        """Test that CompletedUseCase initializes correctly with valid dependencies."""
        use_case = CompletedSaleUseCase(
            order_services=mock_order_services,
            sale_service=mock_sales_service,
            error_queue=mock_error_queue,
        )

        assert use_case.order_services is mock_order_services
        assert use_case.sale_service is mock_sales_service
        assert use_case.error_queue is mock_error_queue

    def test_initialization_creates_frozen_dataclass(
        self, mock_order_services, mock_sales_service, mock_error_queue
    ):
        """Test that CompletedUseCase is a frozen dataclass."""
        use_case = CompletedSaleUseCase(
            order_services=mock_order_services,
            sale_service=mock_sales_service,
            error_queue=mock_error_queue,
        )

        with pytest.raises(AttributeError):
            use_case.sale_service = None  # type: ignore


class TestCompletedUseCaseCompleteSales:
    """Tests for the execute method."""

    def test_execute_with_single_provider_and_one_sale(
        self,
        completed_use_case,
        mock_order_services,
        mock_sales_service,
        mock_order,
    ):
        """Test execute with a single sale from one provider."""
        provider_name = "test_provider"
        sale_id = 100
        remote_id = "remote_123"
        mock_order_service = MagicMock()

        # Mock the registry items method
        mock_order_services.items.return_value = [(provider_name, mock_order_service)]

        # Mock completed sales
        mock_sales_service.get_completed_sales.return_value = [(sale_id, remote_id)]

        # Mock order loading
        mock_order_service.load_order.return_value = mock_order

        completed_use_case.execute()

        # Verify interactions
        mock_sales_service.get_completed_sales.assert_called_once_with(provider_name)
        mock_order_service.load_order.assert_called_once_with(remote_id)
        mock_order_service.notify_completed_sale.assert_called_once_with(mock_order)
        mock_order_service.persist_order.assert_called_once_with(mock_order, OrderStatus.COMPLETED)

    def test_execute_with_multiple_providers(
        self, completed_use_case, mock_order_services, mock_sales_service, mock_order
    ):
        """Test completing sales from multiple providers."""
        provider1 = "provider1"
        provider2 = "provider2"
        mock_order_service1 = MagicMock()
        mock_order_service2 = MagicMock()

        # Mock registry items with multiple providers
        mock_order_services.items.return_value = [
            (provider1, mock_order_service1),
            (provider2, mock_order_service2),
        ]

        # Mock completed sales
        mock_sales_service.get_completed_sales.side_effect = [
            [(1, "remote_1")],
            [(2, "remote_2")],
        ]

        # Mock order loading
        mock_order_service1.load_order.return_value = mock_order
        mock_order_service2.load_order.return_value = mock_order

        completed_use_case.execute()

        # Verify both providers were processed
        assert mock_sales_service.get_completed_sales.call_count == 2
        assert mock_order_service1.load_order.called
        assert mock_order_service2.load_order.called

    def test_execute_with_multiple_sales_per_provider(
        self, completed_use_case, mock_order_services, mock_sales_service, mock_order
    ):
        """Test execute with multiple sales from a single provider."""
        provider_name = "test_provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider_name, mock_order_service)]

        # Return multiple completed sales
        mock_sales_service.get_completed_sales.return_value = [
            (100, "remote_1"),
            (101, "remote_2"),
            (102, "remote_3"),
        ]

        mock_order_service.load_order.return_value = mock_order

        completed_use_case.execute()

        # Verify all sales were processed
        assert mock_sales_service.get_completed_sales.call_count == 1
        assert mock_order_service.load_order.call_count == 3
        assert mock_order_service.notify_completed_sale.call_count == 3
        assert mock_order_service.persist_order.call_count == 3

    def test_execute_skips_when_order_not_found(
        self, completed_use_case, mock_order_services, mock_sales_service
    ):
        """Test that execute skips when order is not found."""
        provider_name = "test_provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider_name, mock_order_service)]
        mock_sales_service.get_completed_sales.return_value = [(100, "remote_123")]

        # Return None to indicate order not found
        mock_order_service.load_order.return_value = None

        completed_use_case.execute()

        # Verify order service methods were not called
        mock_order_service.load_order.assert_called_once()
        mock_order_service.notify_completed_sale.assert_not_called()
        mock_order_service.persist_order.assert_not_called()

    def test_execute_with_no_completed_sales(
        self, completed_use_case, mock_order_services, mock_sales_service
    ):
        """Test execute when there are no completed sales."""
        provider_name = "test_provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider_name, mock_order_service)]

        # Return empty list
        mock_sales_service.get_completed_sales.return_value = []

        completed_use_case.execute()

        # Verify sales service was called but no orders were processed
        mock_sales_service.get_completed_sales.assert_called_once_with(provider_name)
        mock_order_service.load_order.assert_not_called()

    def test_execute_with_no_providers(
        self, completed_use_case, mock_order_services, mock_sales_service
    ):
        """Test execute when there are no registered providers."""
        mock_order_services.items.return_value = []

        completed_use_case.execute()

        # Verify sales service was never called
        mock_sales_service.get_completed_sales.assert_not_called()


class TestCompletedUseCaseErrorHandling:
    """Tests for error handling in execute method."""

    def test_execute_handles_exception_from_get_completed_sales(
        self, completed_use_case, mock_order_services, mock_sales_service, mock_error_queue
    ):
        """Test that exceptions from get_completed_sales are caught and queued."""
        provider_name = "test_provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider_name, mock_order_service)]

        # Raise exception from sales service
        mock_sales_service.get_completed_sales.side_effect = RuntimeError("Service unavailable")

        completed_use_case.execute()

        # Verify error was queued
        mock_error_queue.put.assert_called_once()
        error_arg = mock_error_queue.put.call_args[0][0]
        assert isinstance(error_arg, SaleError)
        assert "test_provider" in str(error_arg)
        assert error_arg.order_id is None

    def test_execute_handles_exception_from_load_order(
        self,
        completed_use_case,
        mock_order_services,
        mock_sales_service,
        mock_error_queue,
    ):
        """Test that exceptions from load_order are caught and queued."""
        provider_name = "test_provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider_name, mock_order_service)]
        mock_sales_service.get_completed_sales.return_value = [(100, "remote_123")]

        # Raise exception from order service
        mock_order_service.load_order.side_effect = ValueError("Invalid order ID")

        completed_use_case.execute()

        # Verify error was queued
        mock_error_queue.put.assert_called_once()
        error_arg = mock_error_queue.put.call_args[0][0]
        assert isinstance(error_arg, SaleError)
        assert "test_provider" in str(error_arg)

    def test_execute_handles_exception_from_notify_completed_sale(
        self,
        completed_use_case,
        mock_order_services,
        mock_sales_service,
        mock_error_queue,
        mock_order,
    ):
        """Test that exceptions from notify_completed_sale are caught and queued."""
        provider_name = "test_provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider_name, mock_order_service)]
        mock_sales_service.get_completed_sales.return_value = [(100, "remote_123")]
        mock_order_service.load_order.return_value = mock_order

        # Raise exception from notify method
        mock_order_service.notify_completed_sale.side_effect = RuntimeError("Notification failed")

        completed_use_case.execute()

        # Verify error was queued
        mock_error_queue.put.assert_called_once()
        error_arg = mock_error_queue.put.call_args[0][0]
        assert isinstance(error_arg, SaleError)
        assert "test_provider" in str(error_arg)

    def test_execute_handles_exception_from_persist_order(
        self,
        completed_use_case,
        mock_order_services,
        mock_sales_service,
        mock_error_queue,
        mock_order,
    ):
        """Test that exceptions from persist_order are caught and queued."""
        provider_name = "test_provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider_name, mock_order_service)]
        mock_sales_service.get_completed_sales.return_value = [(100, "remote_123")]
        mock_order_service.load_order.return_value = mock_order

        # Raise exception from persist method
        mock_order_service.persist_order.side_effect = OSError("Persistence failed")

        completed_use_case.execute()

        # Verify error was queued
        mock_error_queue.put.assert_called_once()
        error_arg = mock_error_queue.put.call_args[0][0]
        assert isinstance(error_arg, SaleError)
        assert "test_provider" in str(error_arg)

    def test_execute_continues_after_exception(
        self,
        completed_use_case,
        mock_order_services,
        mock_sales_service,
        mock_error_queue,
        mock_order,
    ):
        """Test that processing continues with next provider after an exception."""
        provider1 = "provider1"
        provider2 = "provider2"
        mock_order_service1 = MagicMock()
        mock_order_service2 = MagicMock()

        mock_order_services.items.return_value = [
            (provider1, mock_order_service1),
            (provider2, mock_order_service2),
        ]

        # First provider raises exception, second provider succeeds
        mock_sales_service.get_completed_sales.side_effect = [
            RuntimeError("Provider 1 error"),
            [(200, "remote_200")],
        ]

        mock_order_service2.load_order.return_value = mock_order

        completed_use_case.execute()

        # Verify second provider was still processed
        assert mock_sales_service.get_completed_sales.call_count == 2
        mock_order_service2.load_order.assert_called_once()
        assert mock_error_queue.put.call_count == 1


class TestCompletedUseCaseIntegration:
    """Integration tests for complete_sales method."""

    def test_execute_full_workflow(
        self,
        completed_use_case,
        mock_order_services,
        mock_sales_service,
        mock_error_queue,
        mock_order,
    ):
        """Test a complete workflow with multiple providers and sales."""
        provider1 = "provider1"
        provider2 = "provider2"
        mock_order_service1 = MagicMock()
        mock_order_service2 = MagicMock()

        mock_order_services.items.return_value = [
            (provider1, mock_order_service1),
            (provider2, mock_order_service2),
        ]

        mock_sales_service.get_completed_sales.side_effect = [
            [(1, "remote_1"), (2, "remote_2")],
            [(3, "remote_3")],
        ]

        mock_order_service1.load_order.side_effect = [mock_order, mock_order]
        mock_order_service2.load_order.return_value = mock_order

        completed_use_case.execute()

        # Verify all interactions happened correctly
        assert mock_order_service1.notify_completed_sale.call_count == 2
        assert mock_order_service1.persist_order.call_count == 2
        assert mock_order_service2.notify_completed_sale.call_count == 1
        assert mock_order_service2.persist_order.call_count == 1
        mock_error_queue.put.assert_not_called()

    def test_execute_with_mixed_success_and_missing_orders(
        self,
        completed_use_case,
        mock_order_services,
        mock_sales_service,
        mock_error_queue,
        mock_order,
    ):
        """Test execute with some orders existing and some missing."""
        provider = "provider"
        mock_order_service = MagicMock()

        mock_order_services.items.return_value = [(provider, mock_order_service)]
        mock_sales_service.get_completed_sales.return_value = [
            (1, "remote_1"),
            (2, "missing_order"),
            (3, "remote_3"),
        ]

        # Second call returns None to indicate order not found
        mock_order_service.load_order.side_effect = [mock_order, None, mock_order]

        completed_use_case.execute()

        # Verify successful orders were processed
        assert mock_order_service.notify_completed_sale.call_count == 2
        assert mock_order_service.persist_order.call_count == 2
        # Verify missing order error was queued
        mock_error_queue.put.assert_called_once()
        error_arg = mock_error_queue.put.call_args[0][0]
        assert isinstance(error_arg, SaleError)
        assert "missing_order" in str(error_arg)
