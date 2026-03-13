"""Unit tests for StockTransferUseCase."""

from unittest.mock import MagicMock, call

import pytest

from src.app.errors import ErrorStore
from src.app.stock_transfer_use_case import StockTransferUseCase


@pytest.fixture
def mock_stock_services():
    """Create a mock registry for stock services."""
    mock_registry = MagicMock()
    return mock_registry


@pytest.fixture
def stock_transfer_use_case(mock_stock_services):
    """Create a StockTransferUseCase instance with mocked dependencies."""
    return StockTransferUseCase(
        stock_services=mock_stock_services,
    )


class TestStockTransferUseCaseInstantiation:
    """Tests for StockTransferUseCase instantiation."""

    def test_instantiation_with_valid_dependencies(self, mock_stock_services):
        """Test that StockTransferUseCase initializes correctly."""
        use_case = StockTransferUseCase(
            stock_services=mock_stock_services,
        )

        assert use_case.stock_services is mock_stock_services

    def test_instantiation_creates_frozen_dataclass(self, mock_stock_services):
        """Test that StockTransferUseCase is a frozen dataclass."""
        use_case = StockTransferUseCase(
            stock_services=mock_stock_services,
        )

        with pytest.raises(AttributeError):
            use_case.stock_services = None  # type: ignore

    def test_instantiation_requires_stock_services(self):
        """Test that stock_services parameter is required."""
        with pytest.raises(TypeError):
            StockTransferUseCase()  # type: ignore


class TestStockTransferUseCaseExecute:
    """Tests for the execute method."""

    def test_execute_with_no_services(self, stock_transfer_use_case, mock_stock_services):
        """Test execute when no services are registered."""
        mock_stock_services.items.return_value = []

        stock_transfer_use_case.execute()

        mock_stock_services.items.assert_called_once()

    def test_execute_with_single_service_no_transfers(
        self, stock_transfer_use_case, mock_stock_services
    ):
        """Test execute with one service that has no transfers."""
        mock_service = MagicMock()
        mock_service.read_stock_transfers.return_value = []
        mock_stock_services.items.return_value = [("harman", mock_service)]

        stock_transfer_use_case.execute()

        mock_service.read_stock_transfers.assert_called_once()
        mock_service.create_stock_transfer_reply.assert_not_called()
        mock_service.email_stock_transfer_reply.assert_not_called()
        mock_service.mark_transfer_as_processed.assert_not_called()

    def test_execute_with_single_transfer(self, stock_transfer_use_case, mock_stock_services):
        """Test execute with one service and one transfer."""
        mock_service = MagicMock()
        transfer_data = {"id": "transfer_001", "delivery_number": "DEL-001"}
        mock_service.read_stock_transfers.return_value = [transfer_data]
        mock_service.create_stock_transfer_reply.return_value = "/path/to/reply.xml"
        mock_stock_services.items.return_value = [("harman", mock_service)]

        stock_transfer_use_case.execute()

        mock_service.read_stock_transfers.assert_called_once()
        mock_service.create_stock_transfer_reply.assert_called_once_with(transfer_data)
        mock_service.email_stock_transfer_reply.assert_called_once()
        mock_service.mark_transfer_as_processed.assert_called_once_with(transfer_data)

    def test_execute_with_multiple_transfers_from_one_service(
        self, stock_transfer_use_case, mock_stock_services
    ):
        """Test execute with multiple transfers from one service."""
        mock_service = MagicMock()
        transfer1 = {"id": "transfer_001"}
        transfer2 = {"id": "transfer_002"}
        transfer3 = {"id": "transfer_003"}
        mock_service.read_stock_transfers.return_value = [transfer1, transfer2, transfer3]
        mock_service.create_stock_transfer_reply.return_value = "/path/to/reply.xml"
        mock_stock_services.items.return_value = [("harman", mock_service)]

        stock_transfer_use_case.execute()

        assert mock_service.create_stock_transfer_reply.call_count == 3
        assert mock_service.email_stock_transfer_reply.call_count == 3
        assert mock_service.mark_transfer_as_processed.call_count == 3
        mock_service.create_stock_transfer_reply.assert_has_calls(
            [
                call(transfer1),
                call(transfer2),
                call(transfer3),
            ]
        )
        mock_service.mark_transfer_as_processed.assert_has_calls(
            [
                call(transfer1),
                call(transfer2),
                call(transfer3),
            ]
        )

    def test_execute_with_multiple_services(self, stock_transfer_use_case, mock_stock_services):
        """Test execute with multiple services."""
        mock_service1 = MagicMock()
        mock_service1.read_stock_transfers.return_value = [{"id": "t1"}]
        mock_service1.create_stock_transfer_reply.return_value = "/path/to/reply1.xml"

        mock_service2 = MagicMock()
        mock_service2.read_stock_transfers.return_value = [{"id": "t2"}, {"id": "t3"}]
        mock_service2.create_stock_transfer_reply.return_value = "/path/to/reply2.xml"

        mock_stock_services.items.return_value = [
            ("harman", mock_service1),
            ("dhl", mock_service2),
        ]

        stock_transfer_use_case.execute()

        mock_service1.read_stock_transfers.assert_called_once()
        assert mock_service1.create_stock_transfer_reply.call_count == 1
        assert mock_service1.email_stock_transfer_reply.call_count == 1
        assert mock_service1.mark_transfer_as_processed.call_count == 1

        mock_service2.read_stock_transfers.assert_called_once()
        assert mock_service2.create_stock_transfer_reply.call_count == 2
        assert mock_service2.email_stock_transfer_reply.call_count == 2
        assert mock_service2.mark_transfer_as_processed.call_count == 2

    def test_execute_handles_exception_in_reply(
        self, stock_transfer_use_case, mock_stock_services, mocker
    ):
        """Test that execute catches exceptions during reply."""
        mock_service = MagicMock()
        transfer_data = {"id": "transfer_001"}
        mock_service.read_stock_transfers.return_value = [transfer_data]
        test_exception = RuntimeError("Failed to create reply")
        mock_service.create_stock_transfer_reply.side_effect = test_exception
        mock_stock_services.items.return_value = [("harman", mock_service)]

        # Mock ErrorStore to verify add() was called
        mock_error_store = mocker.Mock(spec=ErrorStore)
        mocker.patch(
            "src.app.stock_transfer_use_case.get_error_store", return_value=mock_error_store
        )

        stock_transfer_use_case.execute()

        mock_error_store.add.assert_called_once_with(test_exception)

    def test_execute_continues_after_exception(
        self, stock_transfer_use_case, mock_stock_services, mocker
    ):
        """Test that execute continues processing after an exception."""
        mock_service = MagicMock()
        transfer1 = {"id": "transfer_001"}
        transfer2 = {"id": "transfer_002"}
        mock_service.read_stock_transfers.return_value = [transfer1, transfer2]

        # First call raises exception, second succeeds
        test_exception = RuntimeError("Failed")
        mock_service.create_stock_transfer_reply.side_effect = [
            test_exception,
            "/path/to/reply.xml",
        ]

        mock_stock_services.items.return_value = [("harman", mock_service)]

        # Mock ErrorStore to verify it was called
        mock_error_store = mocker.Mock(spec=ErrorStore)
        mocker.patch(
            "src.app.stock_transfer_use_case.get_error_store", return_value=mock_error_store
        )

        stock_transfer_use_case.execute()

        assert mock_service.create_stock_transfer_reply.call_count == 2
        mock_error_store.add.assert_called_once_with(test_exception)

    def test_execute_with_multiple_services_continues_after_error(
        self, stock_transfer_use_case, mock_stock_services, mocker
    ):
        """Test that execute continues to next service after an error."""
        mock_service1 = MagicMock()
        mock_service1.read_stock_transfers.return_value = [{"id": "t1"}]
        test_exception = RuntimeError("Service 1 failed")
        mock_service1.create_stock_transfer_reply.side_effect = test_exception

        mock_service2 = MagicMock()
        mock_service2.read_stock_transfers.return_value = [{"id": "t2"}]
        mock_service2.create_stock_transfer_reply.return_value = "/path/to/reply.xml"

        mock_stock_services.items.return_value = [
            ("service1", mock_service1),
            ("service2", mock_service2),
        ]

        # Mock ErrorStore
        mock_error_store = mocker.Mock(spec=ErrorStore)
        mocker.patch(
            "src.app.stock_transfer_use_case.get_error_store", return_value=mock_error_store
        )

        stock_transfer_use_case.execute()

        mock_service1.create_stock_transfer_reply.assert_called_once()
        mock_service2.create_stock_transfer_reply.assert_called_once()
        mock_error_store.add.assert_called_once_with(test_exception)

    def test_execute_with_empty_transfer_data(self, stock_transfer_use_case, mock_stock_services):
        """Test execute with empty transfer data dict."""
        mock_service = MagicMock()
        transfer_data = {}
        mock_service.read_stock_transfers.return_value = [transfer_data]
        mock_service.create_stock_transfer_reply.return_value = "/path/to/reply.xml"
        mock_stock_services.items.return_value = [("harman", mock_service)]

        stock_transfer_use_case.execute()

        mock_service.create_stock_transfer_reply.assert_called_once_with(transfer_data)

    def test_execute_calls_read_stock_transfers_once(
        self, stock_transfer_use_case, mock_stock_services
    ):
        """Test that read_stock_transfers is called once per service."""
        mock_service = MagicMock()
        mock_service.read_stock_transfers.return_value = []
        mock_stock_services.items.return_value = [("harman", mock_service)]

        stock_transfer_use_case.execute()

        mock_service.read_stock_transfers.assert_called_once()
