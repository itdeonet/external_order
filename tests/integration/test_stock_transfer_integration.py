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
        service.create_stock_transfer_reply = Mock(return_value="/path/to/reply.xml")
        service.email_stock_transfer_reply = Mock()
        service.mark_transfer_as_processed = Mock()
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

        # Verify that replies were created, emailed, and marked as processed
        assert stock_service.create_stock_transfer_reply.call_count >= 1
        assert stock_service.email_stock_transfer_reply.call_count >= 1
        assert stock_service.mark_transfer_as_processed.call_count >= 1

    def test_stock_transfer_multiple_services(
        self,
        error_store,
    ):
        """Test processing stock transfers from multiple services."""
        service1 = Mock()
        service1.read_stock_transfers.return_value = [
            {"id": "XFER001", "location": "A"},
        ]
        service1.create_stock_transfer_reply = Mock(return_value="/path/to/reply1.xml")
        service1.email_stock_transfer_reply = Mock()
        service1.mark_transfer_as_processed = Mock()

        service2 = Mock()
        service2.read_stock_transfers.return_value = [
            {"id": "XFER002", "location": "B"},
        ]
        service2.create_stock_transfer_reply = Mock(return_value="/path/to/reply2.xml")
        service2.email_stock_transfer_reply = Mock()
        service2.mark_transfer_as_processed = Mock()

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
        service1.create_stock_transfer_reply.assert_called_once()
        service2.create_stock_transfer_reply.assert_called_once()
        service1.email_stock_transfer_reply.assert_called_once()
        service2.email_stock_transfer_reply.assert_called_once()
        service1.mark_transfer_as_processed.assert_called_once()
        service2.mark_transfer_as_processed.assert_called_once()

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

        # Verify the service was called but no replies were created/sent/processed
        stock_service.read_stock_transfers.assert_called_once()
        stock_service.create_stock_transfer_reply.assert_not_called()
        stock_service.email_stock_transfer_reply.assert_not_called()
        stock_service.mark_transfer_as_processed.assert_not_called()

    def test_stock_transfer_error_handling(
        self,
        stock_services,
        error_store,
    ):
        """Test error handling during stock transfer reply."""
        stock_service = stock_services.get("TestStockService")
        stock_service.email_stock_transfer_reply.side_effect = Exception("Email failure")

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
        stock_service.create_stock_transfer_reply = Mock(return_value="/path/to/reply.xml")

        # Make the email fail for the second transfer
        call_count = [0]

        def email_side_effect(reply_path, transfer):
            call_count[0] += 1
            if transfer["id"] == "XFER002":
                raise Exception("Transfer email failed")

        stock_service.email_stock_transfer_reply.side_effect = email_side_effect
        stock_service.mark_transfer_as_processed = Mock()

        stock_services = Registry()
        stock_services.register("TestStockService", stock_service)

        use_case = StockTransferUseCase(
            stock_services=stock_services,
        )

        # Execute the use case
        use_case.execute()

        # Verify all transfers were attempted (3 calls to email, one of which failed)
        assert stock_service.email_stock_transfer_reply.call_count == 3

        # Verify error was stored
        error_store.add.assert_called()
