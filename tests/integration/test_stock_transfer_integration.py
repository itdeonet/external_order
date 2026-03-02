"""Integration tests for StockTransferUseCase."""

from unittest.mock import Mock

import pytest

from src.app.registry import Registry
from src.app.stock_transfer_use_case import StockTransferUseCase


class TestStockTransferUseCaseIntegration:
    """Integration tests for StockTransferUseCase."""

    @pytest.fixture
    def stock_service_mock(self):
        """Provide a mock stock service."""
        service = Mock()
        service.read_stock_transfers.return_value = [
            {"id": "XFER001", "location": "Warehouse A", "quantity": 100},
            {"id": "XFER002", "location": "Warehouse B", "quantity": 50},
        ]
        service.reply_stock_transfer = Mock()
        return service

    @pytest.fixture
    def stock_services(self, stock_service_mock):
        """Provide a registry with a mock stock service."""
        registry = Registry()
        registry.register("TestStockService", stock_service_mock)
        return registry

    def test_stock_transfer_processing(
        self,
        stock_services,
        error_store,
    ):
        """Test that stock transfers are properly processed."""
        use_case = StockTransferUseCase(
            stock_services=stock_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify that stock transfers were read
        stock_service = stock_services.get("TestStockService")
        stock_service.read_stock_transfers.assert_called_once()

        # Verify that replies were sent
        assert stock_service.reply_stock_transfer.call_count >= 1

    def test_stock_transfer_multiple_services(
        self,
        error_store,
    ):
        """Test processing stock transfers from multiple services."""
        service1 = Mock()
        service1.read_stock_transfers.return_value = [
            {"id": "XFER001", "location": "A"},
        ]
        service1.reply_stock_transfer = Mock()

        service2 = Mock()
        service2.read_stock_transfers.return_value = [
            {"id": "XFER002", "location": "B"},
        ]
        service2.reply_stock_transfer = Mock()

        stock_services = Registry()
        stock_services.register("Service1", service1)
        stock_services.register("Service2", service2)

        use_case = StockTransferUseCase(
            stock_services=stock_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify both services were processed
        service1.read_stock_transfers.assert_called_once()
        service2.read_stock_transfers.assert_called_once()
        service1.reply_stock_transfer.assert_called_once()
        service2.reply_stock_transfer.assert_called_once()

    def test_stock_transfer_no_transfers(
        self,
        stock_services,
        error_store,
    ):
        """Test when there are no stock transfers to process."""
        stock_service = stock_services.get("TestStockService")
        stock_service.read_stock_transfers.return_value = []

        use_case = StockTransferUseCase(
            stock_services=stock_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify the service was called but no replies were sent
        stock_service.read_stock_transfers.assert_called_once()
        stock_service.reply_stock_transfer.assert_not_called()

    def test_stock_transfer_error_handling(
        self,
        stock_services,
        error_store,
    ):
        """Test error handling during stock transfer reply."""
        stock_service = stock_services.get("TestStockService")
        stock_service.reply_stock_transfer.side_effect = Exception("Shipping failure")

        use_case = StockTransferUseCase(
            stock_services=stock_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify error was stored
        error_store.add.assert_called()

    def test_stock_transfer_no_services(
        self,
        error_store,
    ):
        """Test when there are no stock services registered."""
        stock_services = Registry()

        use_case = StockTransferUseCase(
            stock_services=stock_services,
        )

        # Execute the use case with empty registry
        use_case.execute()

        # Verify no errors were stored
        error_store.add.assert_not_called()

    def test_stock_transfer_individual_error_isolation(
        self,
        error_store,
    ):
        """Test that error in one transfer doesn't stop processing others."""
        transfers = [
            {"id": "XFER001", "location": "A"},
            {"id": "XFER002", "location": "B"},
            {"id": "XFER003", "location": "C"},
        ]

        stock_service = Mock()
        stock_service.read_stock_transfers.return_value = transfers

        # Make the second transfer fail
        def reply_side_effect(transfer):
            if transfer["id"] == "XFER002":
                raise Exception("Transfer failed")

        stock_service.reply_stock_transfer.side_effect = reply_side_effect

        stock_services = Registry()
        stock_services.register("TestStockService", stock_service)

        use_case = StockTransferUseCase(
            stock_services=stock_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify all transfers were attempted (3 calls total, one of which failed)
        assert stock_service.reply_stock_transfer.call_count == 3

        # Verify error was stored
        error_store.add.assert_called()
