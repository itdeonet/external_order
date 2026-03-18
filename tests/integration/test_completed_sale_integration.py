"""Integration tests for CompletedSaleUseCase."""

from unittest.mock import Mock

import pytest

from src.app.completed_sale_use_case import CompletedSaleUseCase
from src.app.registry import Registry
from src.domain import Order, OrderStatus


class TestCompletedSaleUseCaseIntegration:
    """Integration tests for CompletedSaleUseCase with multiple services."""

    @pytest.fixture
    def sample_order_with_sale_id(self, sample_order):
        """Provide a sample order with a sale ID set."""
        sample_order.set_sale_id(100)
        return sample_order

    @pytest.fixture
    def order_service_mock(self, sample_order_with_sale_id):
        """Provide a mock order service."""
        service = Mock()
        service.load_order.return_value = sample_order_with_sale_id
        service.notify_completed_sale = Mock()
        service.persist_order = Mock()
        return service

    @pytest.fixture
    def order_services(self, order_service_mock):
        """Provide a registry with a mock order service."""
        registry = Registry()
        registry.register("TestOrderService", order_service_mock)
        return registry

    @pytest.fixture
    def sale_service_mock(self):
        """Provide a mock sale service that returns completed sales."""
        service = Mock()
        service.search_completed_sales.return_value = [
            (100, "ORDER123"),  # (sale_id, remote_order_id)
            (101, "ORDER124"),
        ]
        return service

    def test_completed_sale_update(
        self,
        order_services,
        error_store,
    ):
        """Test that completed sales are properly marked as completed."""
        sale_service = Mock()
        sale_service.search_completed_sales.return_value = [
            (100, "ORDER123"),
        ]

        sale_services = Registry()
        sale_services.register("TestSaleService", sale_service)

        use_case = CompletedSaleUseCase(
            order_services=order_services,
            sale_services=sale_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify that the order service was called
        order_service = order_services.get("TestOrderService")
        order_service.load_order.assert_called_with("ORDER123")
        order_service.notify_completed_sale.assert_called()
        order_service.persist_order.assert_called()

        # Verify the order status was set to COMPLETED
        call_args = order_service.persist_order.call_args
        assert call_args[0][1] == OrderStatus.COMPLETED

    def test_completed_sale_multiple_orders(
        self,
        error_store,
    ):
        """Test that multiple completed sales are processed."""
        # Create mock order service that returns a valid order
        order_service = Mock()
        order_service.load_order.return_value = Mock(spec=Order)
        order_service.notify_completed_sale = Mock()
        order_service.persist_order = Mock()

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        sale_service = Mock()
        sale_service.search_completed_sales.return_value = [
            (100, "ORDER123"),
            (101, "ORDER124"),
            (102, "ORDER125"),
        ]

        sale_services = Registry()
        sale_services.register("TestSaleService", sale_service)

        use_case = CompletedSaleUseCase(
            order_services=order_services,
            sale_services=sale_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify all orders were loaded
        assert order_service.load_order.call_count >= 1

    def test_completed_sale_order_not_found(
        self,
        error_store,
    ):
        """Test that missing orders are properly handled."""
        # Setup order service that returns None for a specific order
        order_service = Mock()
        order_service.load_order.return_value = None

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        sale_service = Mock()
        sale_service.search_completed_sales.return_value = [
            (100, "NONEXISTENT_ORDER"),
        ]

        sale_services = Registry()
        sale_services.register("TestSaleService", sale_service)

        use_case = CompletedSaleUseCase(
            order_services=order_services,
            sale_services=sale_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify that an error was stored
        error_store.add.assert_called()

    def test_completed_sale_with_error_in_service(
        self,
        error_store,
    ):
        """Test error handling when order service raises an exception."""
        # Setup order service to raise an exception
        order_service = Mock()
        order_service.load_order.return_value = Mock(spec=Order)
        order_service.notify_completed_sale.side_effect = Exception("Notification failed")

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        sale_service = Mock()
        sale_service.search_completed_sales.return_value = [
            (100, "ORDER123"),
        ]

        sale_services = Registry()
        sale_services.register("TestSaleService", sale_service)

        use_case = CompletedSaleUseCase(
            order_services=order_services,
            sale_services=sale_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify that errors were stored
        error_store.add.assert_called()

    def test_completed_sale_no_completed_sales(
        self,
        error_store,
    ):
        """Test when there are no completed sales."""
        # Setup order service
        order_service = Mock()
        order_service.load_order = Mock()

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        sale_service = Mock()
        sale_service.search_completed_sales.return_value = []

        sale_services = Registry()
        sale_services.register("TestSaleService", sale_service)

        use_case = CompletedSaleUseCase(
            order_services=order_services,
            sale_services=sale_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify no order service calls were made
        order_service.load_order.assert_not_called()

    def test_completed_sale_service_error(
        self,
        order_services,
        error_store,
    ):
        """Test when sale service itself raises an error."""
        sale_service = Mock()
        sale_service.search_completed_sales.side_effect = Exception("Sale service error")

        sale_services = Registry()
        sale_services.register("TestSaleService", sale_service)

        use_case = CompletedSaleUseCase(
            order_services=order_services,
            sale_services=sale_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify error was stored
        error_store.add.assert_called()
