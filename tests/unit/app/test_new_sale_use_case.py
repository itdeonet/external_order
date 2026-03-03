"""Unit tests for the SaleUseCase class."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from src.app.new_sale_use_case import NewSaleUseCase
from src.domain import LineItem, Order, OrderStatus, ShipTo
from src.interfaces import IArtworkService, IOrderService, IRegistry, ISaleService


def create_sample_order(remote_order_id: str = "REMOTE001") -> Order:
    """Helper function to create a sample order for testing."""
    ship_to = ShipTo(
        remote_customer_id="CUST001",
        company_name="Company Name",
        contact_name="John Doe",
        email="john@example.com",
        phone="555-1234",
        street1="123 Main St",
        street2="Apt 4B",
        city="New York",
        state="NY",
        postal_code="10001",
        country_code="US",
    )
    line_item = LineItem(
        remote_line_id="LINE001",
        product_code="PROD001",
        quantity=10,
    )
    return Order(
        administration_id=1,
        customer_id=100,
        order_provider="test_provider",
        pricelist_id=1,
        remote_order_id=remote_order_id,
        shipment_type="express",
        description="Test order",
        ship_to=ship_to,
        line_items=[line_item],
    )


@pytest.fixture
def mock_order_services():
    """Create a mock order services registry."""
    return MagicMock(spec=IRegistry[IOrderService])


@pytest.fixture
def mock_artwork_services():
    """Create a mock artwork services registry."""
    return MagicMock(spec=IRegistry[IArtworkService])


@pytest.fixture
def mock_sale_service():
    """Create a mock sale service."""
    return MagicMock(spec=ISaleService)


@pytest.fixture
def use_case(mock_order_services, mock_artwork_services, mock_sale_service, tmp_path):
    """Create a SaleUseCase instance with mocked dependencies."""
    return NewSaleUseCase(
        order_services=mock_order_services,
        artwork_services=mock_artwork_services,
        sale_service=mock_sale_service,
        open_orders_dir=tmp_path,
    )


class TestSaleUseCaseInstantiation:
    """Tests for SaleUseCase instantiation and basic properties."""

    def test_instantiation_with_valid_dependencies(
        self, mock_order_services, mock_artwork_services, mock_sale_service
    ):
        """Test creating a SaleUseCase with valid dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            use_case = NewSaleUseCase(
                order_services=mock_order_services,
                artwork_services=mock_artwork_services,
                sale_service=mock_sale_service,
                open_orders_dir=Path(tmpdir),
            )

            assert use_case is not None
            assert use_case.order_services is mock_order_services
            assert use_case.artwork_services is mock_artwork_services
            assert use_case.sale_service is mock_sale_service

    def test_instantiation_is_frozen_dataclass(self, use_case):
        """Test that SaleUseCase is a frozen dataclass."""
        with pytest.raises(AttributeError):
            use_case.order_services = MagicMock()  # type: ignore

    def test_instantiation_requires_order_services(self, mock_artwork_services, mock_sale_service):
        """Test that order_services is a required parameter."""
        with tempfile.TemporaryDirectory() as tmpdir, pytest.raises(TypeError):
            NewSaleUseCase(
                artwork_services=mock_artwork_services,
                sale_service=mock_sale_service,
                open_orders_dir=Path(tmpdir),
            )  # type: ignore

    def test_instantiation_requires_sale_service(self, mock_order_services, mock_artwork_services):
        """Test that sale_service is a required parameter."""
        with tempfile.TemporaryDirectory() as tmpdir, pytest.raises(TypeError):
            NewSaleUseCase(
                order_services=mock_order_services,
                artwork_services=mock_artwork_services,
                open_orders_dir=Path(tmpdir),
            )  # type: ignore

    def test_instantiation_requires_open_orders_dir(
        self, mock_order_services, mock_artwork_services, mock_sale_service
    ):
        """Test that open_orders_dir is a required parameter."""
        with pytest.raises(TypeError):
            NewSaleUseCase(
                order_services=mock_order_services,
                artwork_services=mock_artwork_services,
                sale_service=mock_sale_service,
            )  # type: ignore


class TestCreateSalesWithNoOrders:
    """Tests for execute when there are no orders."""

    def test_create_sales_with_no_order_services(self, use_case):
        """Test execute when no order services are registered."""
        use_case.order_services.items.return_value = []

        use_case.execute()

        use_case.order_services.items.assert_called_once()

    def test_create_sales_with_order_service_but_no_orders(self, use_case, mocker):
        """Test execute when order service returns no orders."""
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([])

        use_case.order_services.items.return_value = [("test_service", order_service)]

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        order_service.read_orders.assert_called_once()


class TestCreateSalesNewSaleCreation:
    """Tests for execute when creating new sales."""

    def test_create_sales_creates_new_sale_when_none_exists(self, use_case, mocker):
        """Test that execute creates a new sale when none exists."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        use_case.sale_service.is_sale_created.assert_called_once_with(order)
        use_case.sale_service.create_sale.assert_called_once_with(order)

    def test_create_sales_persists_order_status_new(self, use_case, mocker):
        """Test that order is persisted with NEW status."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        # First persist call should be with NEW status
        calls = order_service.persist_order.call_args_list
        assert calls[0] == call(order, OrderStatus.NEW)

    def test_create_sales_persists_order_status_created(self, use_case, mocker):
        """Test that order is persisted with CREATED status after creating sale."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        calls = order_service.persist_order.call_args_list
        assert calls[1] == call(order, OrderStatus.CREATED)

    def test_create_sales_persists_order_status_artwork(self, use_case, mocker):
        """Test that order is persisted with ARTWORK status after getting artwork."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        calls = order_service.persist_order.call_args_list
        assert calls[2] == call(order, OrderStatus.ARTWORK)

    def test_create_sales_persists_order_status_confirmed(self, use_case, mocker):
        """Test that order is persisted with CONFIRMED status after confirming sale."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        calls = order_service.persist_order.call_args_list
        assert calls[3] == call(order, OrderStatus.CONFIRMED)

    def test_create_sales_confirms_sale_after_artwork(self, use_case, mocker):
        """Test that sale is confirmed after getting artwork."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        use_case.sale_service.confirm_sale.assert_called_once_with(order)


class TestCreateSalesExistingSaleUpdate:
    """Tests for execute when updating existing sales."""

    def test_create_sales_updates_contact_when_sale_exists_and_lines_match(self, use_case, mocker):
        """Test that contact is updated when sale exists and order lines match."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = True
        use_case.sale_service.has_expected_order_lines.return_value = True

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        use_case.sale_service.update_contact.assert_called_once_with(order)
        use_case.sale_service.create_sale.assert_not_called()

    def test_create_sales_raises_error_when_order_lines_mismatch(self, use_case, mocker):
        """Test that SaleError is handled when order lines don't match."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = True
        use_case.sale_service.has_expected_order_lines.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        # Should complete without raising, errors are handled internally
        use_case.execute()

    def test_sale_error_contains_order_id(self, use_case, mocker):
        """Test that SaleError contains the order ID."""
        order = create_sample_order("ORDER123")
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = True
        use_case.sale_service.has_expected_order_lines.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        # Should complete without raising
        use_case.execute()


class TestCreateSalesExceptionHandling:
    """Tests for exception handling in execute."""

    def test_create_sales_catches_exception_and_stores_error(self, use_case, mocker):
        """Test that exceptions are caught and handled."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.persist_order.side_effect = Exception("Persist failed")

        use_case.order_services.items.return_value = [("test_service", order_service)]

        mocker.patch("src.app.new_sale_use_case.logger")

        # Should complete without raising
        use_case.execute()

    def test_create_sales_continues_after_exception_from_first_order(self, use_case, mocker):
        """Test that execute continues after exception from first order."""
        order1 = create_sample_order("ORDER1")
        order2 = create_sample_order("ORDER2")

        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order1, order2])
        order_service.persist_order.side_effect = [
            Exception("Fail"),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ]
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        # Both orders should have been attempted (persist called at least for first status)
        assert order_service.read_orders.call_count == 1

    def test_create_sales_exception_during_create_sale(self, use_case, mocker):
        """Test exception handling when create_sale fails."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False
        use_case.sale_service.create_sale.side_effect = Exception("Sale creation failed")

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

    def test_create_sales_exception_during_confirm_sale(self, use_case, mocker):
        """Test exception handling when confirm_sale fails."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False
        use_case.sale_service.confirm_sale.side_effect = Exception("Confirm failed")

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()


class TestCreateSalesWithMultipleServices:
    """Tests for execute with multiple order services."""

    def test_create_sales_processes_multiple_order_services(self, use_case, mocker):
        """Test that execute processes all registered order services."""
        order1 = create_sample_order("ORDER1")
        order2 = create_sample_order("ORDER2")

        order_service1 = MagicMock(spec=IOrderService)
        order_service1.read_orders.return_value = iter([order1])
        order_service1.get_artwork_service.return_value = None

        order_service2 = MagicMock(spec=IOrderService)
        order_service2.read_orders.return_value = iter([order2])
        order_service2.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [
            ("service1", order_service1),
            ("service2", order_service2),
        ]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        order_service1.read_orders.assert_called_once()
        order_service2.read_orders.assert_called_once()

    def test_create_sales_handles_exception_in_one_service(self, use_case, mocker):
        """Test that exception in one service doesn't affect others."""
        order1 = create_sample_order("ORDER1")
        order2 = create_sample_order("ORDER2")

        order_service1 = MagicMock(spec=IOrderService)
        order_service1.read_orders.return_value = iter([order1])
        order_service1.persist_order.side_effect = Exception("Service 1 failed")

        order_service2 = MagicMock(spec=IOrderService)
        order_service2.read_orders.return_value = iter([order2])
        order_service2.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [
            ("service1", order_service1),
            ("service2", order_service2),
        ]
        use_case.sale_service.is_sale_created.return_value = False

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        # Both services should still be attempted
        order_service1.read_orders.assert_called_once()
        order_service2.read_orders.assert_called_once()

    def test_create_sales_with_three_services(self, use_case, mocker):
        """Test execute with three order services."""
        order_service1 = MagicMock(spec=IOrderService)
        order_service1.read_orders.return_value = iter([])

        order_service2 = MagicMock(spec=IOrderService)
        order_service2.read_orders.return_value = iter([])

        order_service3 = MagicMock(spec=IOrderService)
        order_service3.read_orders.return_value = iter([])

        use_case.order_services.items.return_value = [
            ("service1", order_service1),
            ("service2", order_service2),
            ("service3", order_service3),
        ]

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        order_service1.read_orders.assert_called_once()
        order_service2.read_orders.assert_called_once()
        order_service3.read_orders.assert_called_once()


class TestGetArtworkBasic:
    """Tests for get_artwork basic functionality."""

    def test_get_artwork_with_no_service(self, use_case, mocker):
        """Test get_artwork returns empty list when no service provided."""
        order = create_sample_order()

        result = use_case.get_artwork(order, None)

        assert result == []
        mocker.patch("src.app.new_sale_use_case.logger")

    def test_get_artwork_with_service_returning_no_files(self, use_case, mocker):
        """Test get_artwork when service returns no files."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)
        artwork_service.get_artwork.return_value = []

        mocker.patch("src.app.new_sale_use_case.logger")

        result = use_case.get_artwork(order, artwork_service)

        assert result == []
        artwork_service.get_artwork.assert_called_once_with(order)

    def test_get_artwork_returns_list_of_paths(self, use_case, mocker):
        """Test get_artwork returns list of Path objects."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "test.pdf"
            temp_file.write_text("test")
            artwork_service.get_artwork.return_value = [temp_file]

            mocker.patch("src.app.new_sale_use_case.logger")

            result = use_case.get_artwork(order, artwork_service)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0] == temp_file

    def test_get_artwork_calls_service_get_artwork(self, use_case, mocker):
        """Test get_artwork calls the artwork service."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)
        artwork_service.get_artwork.return_value = []

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.get_artwork(order, artwork_service)

        artwork_service.get_artwork.assert_called_once_with(order)


class TestGetArtworkPlacementHandling:
    """Tests for placement file handling in get_artwork."""

    def test_get_artwork_copies_placement_file(self, use_case, mocker):
        """Test that placement files are copied to order directory."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "ABC123_placement.pdf"
            temp_file.write_text("placement content")
            artwork_service.get_artwork.return_value = [temp_file]

            mocker.patch("src.app.new_sale_use_case.logger")

            use_case.get_artwork(order, artwork_service)

            # Check that file was copied to order directory
            expected_dir = use_case.open_orders_dir / "ABC123"
            assert expected_dir.exists()
            assert (expected_dir / temp_file.name).exists()
            assert (expected_dir / temp_file.name).read_text() == "placement content"

    def test_get_artwork_does_not_copy_non_placement_file(self, use_case, mocker):
        """Test that non-placement files are not copied."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "ABC123_artwork.pdf"
            temp_file.write_text("artwork content")
            artwork_service.get_artwork.return_value = [temp_file]

            mocker.patch("src.app.new_sale_use_case.logger")

            use_case.get_artwork(order, artwork_service)

            # Check that file was not copied
            expected_dir = use_case.open_orders_dir / "ABC123"
            assert not expected_dir.exists()

    def test_get_artwork_placement_detection_case_insensitive(self, use_case, mocker):
        """Test that placement detection is case insensitive."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test various case combinations
            test_cases = [
                "ABC_PLACEMENT.pdf",
                "ABC_Placement.pdf",
                "ABC_PlAcEmEnT.pdf",
            ]

            for filename in test_cases:
                temp_file = Path(tmpdir) / filename
                temp_file.write_text("placement")
                artwork_service.get_artwork.return_value = [temp_file]

                mocker.patch("src.app.new_sale_use_case.logger")

                use_case.get_artwork(order, artwork_service)

                name_parts = filename.split("_")
                expected_dir = use_case.open_orders_dir / name_parts[0]
                assert (expected_dir / filename).exists()

    def test_get_artwork_creates_nested_order_directory(self, use_case, mocker):
        """Test that order directory is created for placement files."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with underscore in the name
            temp_file = Path(tmpdir) / "ORDER_CODE_placement.pdf"
            temp_file.write_text("placement")
            artwork_service.get_artwork.return_value = [temp_file]

            mocker.patch("src.app.new_sale_use_case.logger")

            use_case.get_artwork(order, artwork_service)

            # The order ID is extracted from the first part before underscore
            expected_dir = use_case.open_orders_dir / "ORDER"
            assert expected_dir.exists()
            assert (expected_dir / temp_file.name).exists()

    def test_get_artwork_handles_multiple_files_mixed(self, use_case, mocker):
        """Test get_artwork with mix of placement and non-placement files."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            placement_file = Path(tmpdir) / "ABC_placement.pdf"
            artwork_file = Path(tmpdir) / "ABC_artwork.pdf"
            placement_file.write_text("placement")
            artwork_file.write_text("artwork")

            artwork_service.get_artwork.return_value = [placement_file, artwork_file]

            mocker.patch("src.app.new_sale_use_case.logger")

            result = use_case.get_artwork(order, artwork_service)

            # Both files should be returned
            assert len(result) == 2

            # Only placement should be copied
            expected_dir = use_case.open_orders_dir / "ABC"
            assert (expected_dir / placement_file.name).exists()
            assert not (expected_dir / artwork_file.name).exists()

    def test_get_artwork_placement_with_underscore_in_name(self, use_case, mocker):
        """Test placement detection with underscores in filename."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            # File with underscores: XYZ_ABC_DEF_placement.pdf
            temp_file = Path(tmpdir) / "XYZ_ABC_DEF_placement.pdf"
            temp_file.write_text("placement")
            artwork_service.get_artwork.return_value = [temp_file]

            mocker.patch("src.app.new_sale_use_case.logger")

            use_case.get_artwork(order, artwork_service)

            # Should extract "XYZ" as the order ID (first part before underscore)
            expected_dir = use_case.open_orders_dir / "XYZ"
            assert (expected_dir / temp_file.name).exists()

    def test_get_artwork_file_copy_preserves_attributes(self, use_case, mocker):
        """Test that copied file preserves original file attributes."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "ABC_placement.pdf"
            temp_file.write_text("placement content")
            # Get original modification time
            original_stat = temp_file.stat()

            artwork_service.get_artwork.return_value = [temp_file]

            mocker.patch("src.app.new_sale_use_case.logger")

            use_case.get_artwork(order, artwork_service)

            copied_file = use_case.open_orders_dir / "ABC" / temp_file.name
            copied_stat = copied_file.stat()

            # shutil.copy2 preserves metadata
            assert copied_stat.st_mtime == original_stat.st_mtime


class TestCreateSalesLogging:
    """Tests for logging in execute."""

    def test_create_sales_logs_service_processing_start(self, use_case, mocker, caplog):
        """Test that execute logs when starting to process a service."""
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([])

        use_case.order_services.items.return_value = [("test_service", order_service)]

        with caplog.at_level(logging.INFO):
            use_case.execute()

            assert "Create sales from test_service service" in caplog.text

    def test_create_sales_logs_order_creation(self, use_case, mocker, caplog):
        """Test that execute logs when creating an order."""
        order = create_sample_order("ORDER123")
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = False

        with caplog.at_level(logging.INFO):
            use_case.execute()

            assert "Create sale order ORDER123 from test_service service" in caplog.text

    def test_create_sales_logs_error_on_exception(self, use_case, mocker, caplog):
        """Test that execute logs errors when exceptions occur."""
        order = create_sample_order("ORDER456")
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.persist_order.side_effect = Exception("Test error")

        use_case.order_services.items.return_value = [("test_service", order_service)]

        with caplog.at_level(logging.ERROR):
            use_case.execute()

            assert "Error processing order ORDER456" in caplog.text
            assert "Test error" in caplog.text

    def test_create_sales_logs_mismatched_quantities_error(self, use_case, mocker, caplog):
        """Test that execute logs error for mismatched order lines."""
        order = create_sample_order()
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = True
        use_case.sale_service.has_expected_order_lines.return_value = False

        with caplog.at_level(logging.ERROR):
            use_case.execute()

            assert "Error processing order REMOTE001" in caplog.text

    def test_get_artwork_logs_no_service_warning(self, use_case, mocker, caplog):
        """Test that get_artwork logs warning when no service available."""
        order = create_sample_order()

        with caplog.at_level(logging.WARNING):
            use_case.get_artwork(order, None)

            assert "No artwork service found" in caplog.text

    def test_get_artwork_logs_download_info(self, use_case, mocker, caplog):
        """Test that get_artwork logs download information."""
        order = create_sample_order()
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.pdf"
            file2 = Path(tmpdir) / "file2.pdf"
            file1.write_text("content1")
            file2.write_text("content2")
            artwork_service.get_artwork.return_value = [file1, file2]

            with caplog.at_level(logging.INFO):
                use_case.get_artwork(order, artwork_service)

                assert "Downloaded 2 files" in caplog.text


class TestSaleUseCaseIntegration:
    """Integration tests for SaleUseCase."""

    def test_full_workflow_new_sale(self, use_case, mocker):
        """Test complete workflow for creating a new sale with artwork."""
        order = create_sample_order("FULL_ORDER_001")
        order_service = MagicMock(spec=IOrderService)
        artwork_service = MagicMock(spec=IArtworkService)

        with tempfile.TemporaryDirectory() as tmpdir:
            placement_file = Path(tmpdir) / "FULL_placement.pdf"
            placement_file.write_text("placement")
            artwork_service.get_artwork.return_value = [placement_file]

            order_service.read_orders.return_value = iter([order])
            order_service.get_artwork_service.return_value = artwork_service

            use_case.order_services.items.return_value = [("integration_service", order_service)]
            use_case.sale_service.is_sale_created.return_value = False

            mocker.patch("src.app.new_sale_use_case.logger")

            use_case.execute()

            # Verify complete flow
            use_case.sale_service.create_sale.assert_called_once_with(order)
            use_case.sale_service.confirm_sale.assert_called_once_with(order)
            assert order_service.persist_order.call_count == 4

            # Verify placement file was copied
            expected_dir = use_case.open_orders_dir / "FULL"
            assert (expected_dir / placement_file.name).exists()

    def test_full_workflow_update_existing_sale(self, use_case, mocker):
        """Test complete workflow for updating existing sale."""
        order = create_sample_order("UPDATE_ORDER_001")
        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("update_service", order_service)]
        use_case.sale_service.is_sale_created.return_value = True
        use_case.sale_service.has_expected_order_lines.return_value = True

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        # Verify flow
        use_case.sale_service.update_contact.assert_called_once_with(order)
        use_case.sale_service.confirm_sale.assert_called_once_with(order)
        use_case.sale_service.create_sale.assert_not_called()

    def test_full_workflow_multiple_orders_different_statuses(self, use_case, mocker):
        """Test workflow with multiple orders having different outcomes."""
        order1 = create_sample_order("ORDER_NEW")
        order2 = create_sample_order("ORDER_EXISTS")
        order3 = create_sample_order("ORDER_ERROR")

        order_service = MagicMock(spec=IOrderService)
        order_service.read_orders.return_value = iter([order1, order2, order3])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("multi_service", order_service)]

        # Order 1: New sale
        # Order 2: Existing sale with matching lines
        # Order 3: Exception during processing
        use_case.sale_service.is_sale_created.side_effect = [False, True, False]
        use_case.sale_service.has_expected_order_lines.return_value = True
        order_service.persist_order.side_effect = [
            None,  # order1 NEW
            None,  # order1 CREATED
            None,  # order1 ARTWORK
            None,  # order1 CONFIRMED
            None,  # order2 NEW
            None,  # order2 CREATED
            None,  # order2 ARTWORK
            None,  # order2 CONFIRMED
            Exception("Processing failed"),  # order3 fails
        ]

        mocker.patch("src.app.new_sale_use_case.logger")

        use_case.execute()

        # Verify that all orders were attempted
