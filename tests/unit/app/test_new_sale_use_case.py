"""Unit tests for the NewSaleUseCase class."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.app.errors import SaleError
from src.app.new_sale_use_case import NewSaleUseCase
from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.interfaces.ierror_queue import IErrorQueue
from src.domain.interfaces.iorder_service import IOrderService
from src.domain.interfaces.iregistry import IRegistry
from src.domain.interfaces.isales_service import ISalesService
from src.domain.line_item import LineItem
from src.domain.order import Order, OrderStatus
from src.domain.ship_to import ShipTo


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
        product_id="PROD001",
        quantity=10,
    )
    return Order(
        administration_id=1,
        customer_id=100,
        order_provider="test_provider",
        pricelist_id=1,
        remote_order_id=remote_order_id,
        shipment_type="express",
        ship_to=ship_to,
        line_items=[line_item],
    )


class TestNewSaleUseCaseInstantiation:
    """Tests for NewSaleUseCase instantiation."""

    @pytest.fixture
    def dependencies(self):
        """Create mock dependencies."""
        return {
            "order_services": MagicMock(spec=IRegistry),
            "artwork_services": MagicMock(spec=IRegistry),
            "sales_service": MagicMock(spec=ISalesService),
            "error_queue": MagicMock(spec=IErrorQueue),
            "open_orders_dir": Path("/tmp/orders"),
        }

    def test_instantiation(self, dependencies):
        """Test creating a NewSaleUseCase instance."""
        use_case = NewSaleUseCase(**dependencies)
        assert use_case is not None

    def test_instantiation_with_frozen_dataclass(self, dependencies):
        """Test that NewSaleUseCase is frozen."""
        use_case = NewSaleUseCase(**dependencies)
        with pytest.raises(AttributeError):
            use_case.order_services = MagicMock()  # type: ignore

    def test_instantiation_attributes(self, dependencies):
        """Test that all attributes are properly set."""
        use_case = NewSaleUseCase(**dependencies)
        assert use_case.order_services is dependencies["order_services"]
        assert use_case.artwork_services is dependencies["artwork_services"]
        assert use_case.sales_service is dependencies["sales_service"]
        assert use_case.error_queue is dependencies["error_queue"]
        assert use_case.open_orders_dir == dependencies["open_orders_dir"]


class TestNewSaleUseCaseCreateOrUpdateSale:
    """Tests for CreateOrUpdateSale method."""

    @pytest.fixture
    def use_case_dependencies(self):
        """Create mock dependencies for use case."""
        return {
            "order_services": MagicMock(spec=IRegistry),
            "artwork_services": MagicMock(spec=IRegistry),
            "sales_service": MagicMock(spec=ISalesService),
            "error_queue": MagicMock(spec=IErrorQueue),
            "open_orders_dir": Path("/tmp/orders"),
        }

    @pytest.fixture
    def use_case(self, use_case_dependencies):
        """Create a NewSaleUseCase instance."""
        return NewSaleUseCase(**use_case_dependencies)

    @pytest.fixture
    def sample_order(self):
        """Create a sample order."""
        return create_sample_order()

    def test_create_new_sale_when_no_existing_sale(self, use_case, sample_order):
        """Test creating a new sale when no existing sale found."""
        use_case.sales_service.get_sale.return_value = None
        use_case.sales_service.create_sale.return_value = 42

        use_case.create_or_update_sale(sample_order)

        use_case.sales_service.get_sale.assert_called_once_with(sample_order)
        use_case.sales_service.create_sale.assert_called_once_with(sample_order)
        assert sample_order.id == 42

    def test_update_existing_sale_with_matching_quantities(self, use_case, sample_order):
        """Test updating an existing sale with matching quantities."""
        existing_sale = {"id": 99}
        use_case.sales_service.get_sale.return_value = existing_sale
        use_case.sales_service.verify_sale_quantities.return_value = True

        use_case.create_or_update_sale(sample_order)

        assert sample_order.id == 99
        use_case.sales_service.update_contact.assert_called_once_with(sample_order)
        use_case.sales_service.confirm_sale.assert_called_once_with(99)

    def test_update_existing_sale_with_mismatched_quantities(self, use_case, sample_order):
        """Test updating an existing sale with mismatched quantities."""
        existing_sale = {"id": 99}
        use_case.sales_service.get_sale.return_value = existing_sale
        use_case.sales_service.verify_sale_quantities.return_value = False

        with pytest.raises(SaleError) as exc_info:
            use_case.create_or_update_sale(sample_order)

        assert "Sale order line quantities do not match" in str(exc_info.value)
        assert exc_info.value.order_id == sample_order.remote_order_id

    def test_sale_id_is_int_from_string(self, use_case, sample_order):
        """Test that sale ID is converted from string to int."""
        existing_sale = {"id": "123"}  # ID as string
        use_case.sales_service.get_sale.return_value = existing_sale
        use_case.sales_service.verify_sale_quantities.return_value = True

        use_case.create_or_update_sale(sample_order)

        assert sample_order.id == 123
        assert isinstance(sample_order.id, int)


class TestNewSaleUseCaseGetArtwork:
    """Tests for GetArtwork method."""

    @pytest.fixture
    def use_case_dependencies(self):
        """Create mock dependencies for use case."""
        return {
            "order_services": MagicMock(spec=IRegistry),
            "artwork_services": MagicMock(spec=IRegistry),
            "sales_service": MagicMock(spec=ISalesService),
            "error_queue": MagicMock(spec=IErrorQueue),
            "open_orders_dir": Path(tempfile.gettempdir()) / "orders",
        }

    @pytest.fixture
    def use_case(self, use_case_dependencies):
        """Create a NewSaleUseCase instance."""
        return NewSaleUseCase(**use_case_dependencies)

    @pytest.fixture
    def sample_order(self):
        """Create a sample order."""
        return create_sample_order()

    def test_get_artwork_with_no_service(self, use_case, sample_order):
        """Test getting artwork when no service is available."""
        result = use_case.get_artwork(sample_order, None)

        assert result == []

    def test_get_artwork_with_service_and_no_files(self, use_case, sample_order):
        """Test getting artwork when service returns no files."""
        artwork_service = MagicMock(spec=IArtworkService)
        artwork_service.get_artwork.return_value = []

        result = use_case.get_artwork(sample_order, artwork_service)

        assert result == []
        artwork_service.get_artwork.assert_called_once_with(sample_order)

    def test_get_artwork_with_placement_file(self, use_case, sample_order):
        """Test getting artwork with placement file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            use_case.open_orders_dir.mkdir(parents=True, exist_ok=True)
            artwork_service = MagicMock(spec=IArtworkService)

            # Create a temporary file with "placement" in the name
            temp_file = Path(tmpdir) / "ABC123_placement.pdf"
            temp_file.write_text("test content")

            artwork_service.get_artwork.return_value = [temp_file]

            # Execute
            result = use_case.get_artwork(sample_order, artwork_service)

            # Verify
            assert len(result) == 1
            assert result[0] == temp_file

            # Check that file was copied to order directory
            expected_dir = use_case.open_orders_dir / "ABC123"
            assert expected_dir.exists()
            assert (expected_dir / temp_file.name).exists()

    def test_get_artwork_with_non_placement_file(self, use_case, sample_order):
        """Test getting artwork with non-placement file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            artwork_service = MagicMock(spec=IArtworkService)

            # Create a temporary file without "placement" in the name
            temp_file = Path(tmpdir) / "ABC123_artwork.pdf"
            temp_file.write_text("test content")

            artwork_service.get_artwork.return_value = [temp_file]

            # Execute
            result = use_case.get_artwork(sample_order, artwork_service)

            # Verify
            assert len(result) == 1
            assert result[0] == temp_file
            # Setup
            use_case.open_orders_dir.mkdir(parents=True, exist_ok=True)
            artwork_service = MagicMock(spec=IArtworkService)

            # Create multiple files
            placement_file = Path(tmpdir) / "ABC123_placement.pdf"
            regular_file = Path(tmpdir) / "ABC123_artwork.pdf"
            placement_file.write_text("placement")
            regular_file.write_text("artwork")

            artwork_service.get_artwork.return_value = [placement_file, regular_file]

            # Execute
            result = use_case.get_artwork(sample_order, artwork_service)

            # Verify
            assert len(result) == 2

            # Only placement file should be copied
            expected_dir = use_case.open_orders_dir / "ABC123"
            assert expected_dir.exists()
            assert (expected_dir / placement_file.name).exists()
            assert not (expected_dir / regular_file.name).exists()

    def test_get_artwork_creates_order_directory(self, use_case, sample_order):
        """Test that order directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            artwork_service = MagicMock(spec=IArtworkService)

            # Create a temporary file
            temp_file = Path(tmpdir) / "XYZ789_placement.pdf"
            temp_file.write_text("test")

            artwork_service.get_artwork.return_value = [temp_file]

            # Execute
            use_case.get_artwork(sample_order, artwork_service)

            # Verify directory was created
            expected_dir = use_case.open_orders_dir / "XYZ789"
            assert expected_dir.exists()

    def test_get_artwork_placement_case_insensitive(self, use_case, sample_order):
        """Test that placement detection is case insensitive."""
        with tempfile.TemporaryDirectory():
            use_case_temp_dir = Path(tempfile.gettempdir()) / "test_orders_case_insensitive"
            use_case_temp_dir.mkdir(parents=True, exist_ok=True)

            try:
                test_cases = [
                    "ABC123_PLACEMENT.pdf",
                    "ABC123_Placement.pdf",
                    "ABC123_PlAcEmEnT.pdf",
                ]

                for filename in test_cases:
                    with tempfile.TemporaryDirectory() as file_tmpdir:
                        artwork_service = MagicMock(spec=IArtworkService)
                        temp_file = Path(file_tmpdir) / filename
                        temp_file.write_text("test")
                        artwork_service.get_artwork.return_value = [temp_file]

                        # Create a fresh use case for each case or reuse the temp dir
                        result = use_case.get_artwork(sample_order, artwork_service)
                        assert len(result) == 1
                        # Verify placement file was copied to order directory
                        name_parts = filename.split("_")
                        order_dir = use_case.open_orders_dir / name_parts[0]
                        assert (order_dir / filename).exists()
            finally:
                import shutil as sh

                sh.rmtree(use_case_temp_dir, ignore_errors=True)


class TestNewSaleUseCaseCreateSales:
    """Tests for CreateSales method."""

    @pytest.fixture
    def use_case_dependencies(self):
        """Create mock dependencies for use case."""
        return {
            "order_services": MagicMock(spec=IRegistry),
            "artwork_services": MagicMock(spec=IRegistry),
            "sales_service": MagicMock(spec=ISalesService),
            "error_queue": MagicMock(spec=IErrorQueue),
            "open_orders_dir": Path("/tmp/orders"),
        }

    @pytest.fixture
    def use_case(self, use_case_dependencies):
        """Create a NewSaleUseCase instance."""
        return NewSaleUseCase(**use_case_dependencies)

    @pytest.fixture
    def sample_order(self):
        """Create a sample order."""
        return create_sample_order()

    def test_create_sales_with_no_order_services(self, use_case):
        """Test creating sales with no order services registered."""
        use_case.order_services.items.return_value = []

        use_case.create_sales()

        use_case.order_services.items.assert_called_once()

    def test_create_sales_with_single_order_service(self, use_case, sample_order):
        """Test creating sales with a single order service."""
        order_service = MagicMock(spec=IOrderService)
        order_service.get_orders.return_value = iter([sample_order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sales_service.get_sale.return_value = None
        use_case.sales_service.create_sale.return_value = 42

        use_case.create_sales()

        order_service.get_orders.assert_called_once_with(use_case.error_queue)
        assert order_service.persist_order.call_count == 4  # NEW, CREATED, ARTWORK, CONFIRMED
        # Check the status transitions
        calls = order_service.persist_order.call_args_list
        assert calls[0] == call(sample_order, OrderStatus.NEW)
        assert calls[1] == call(sample_order, OrderStatus.CREATED)
        assert calls[2] == call(sample_order, OrderStatus.ARTWORK)
        assert calls[3] == call(sample_order, OrderStatus.CONFIRMED)

    def test_create_sales_with_exception_puts_error_in_queue(self, use_case, sample_order):
        """Test that exceptions are added to error queue."""
        order_service = MagicMock(spec=IOrderService)
        order_service.get_orders.return_value = iter([sample_order])
        order_service.persist_order.side_effect = Exception("Test error")

        use_case.order_services.items.return_value = [("test_service", order_service)]

        use_case.create_sales()

        use_case.error_queue.put.assert_called()

    def test_create_sales_continues_after_exception(self, use_case, sample_order):
        """Test that create_sales continues processing after an exception."""
        order1 = sample_order
        order2 = create_sample_order("REMOTE002")

        order_service = MagicMock(spec=IOrderService)
        order_service.get_orders.return_value = iter([order1, order2])
        order_service.get_artwork_service.return_value = None

        # First order fails on create_or_update_sale, second succeeds
        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sales_service.get_sale.return_value = None
        use_case.sales_service.create_sale.side_effect = [Exception("Failed"), 43]

        use_case.create_sales()

        # Both orders should have been attempted
        assert order_service.persist_order.call_count >= 2
        assert use_case.error_queue.put.called

    def test_create_sales_with_multiple_order_services(self, use_case, sample_order):
        """Test creating sales with multiple order services."""
        order_service1 = MagicMock(spec=IOrderService)
        order_service1.get_orders.return_value = iter([sample_order])
        order_service1.get_artwork_service.return_value = None

        order_service2 = MagicMock(spec=IOrderService)
        order_service2.get_orders.return_value = iter([])

        use_case.order_services.items.return_value = [
            ("service1", order_service1),
            ("service2", order_service2),
        ]
        use_case.sales_service.get_sale.return_value = None
        use_case.sales_service.create_sale.return_value = 42

        use_case.create_sales()

        order_service1.get_orders.assert_called_once()
        order_service2.get_orders.assert_called_once()

    def test_create_sales_confirms_sale_after_artwork(self, use_case, sample_order):
        """Test that sale is confirmed after artwork is retrieved."""
        order_service = MagicMock(spec=IOrderService)
        order_service.get_orders.return_value = iter([sample_order])
        artwork_service = MagicMock(spec=IArtworkService)
        artwork_service.get_artwork.return_value = []
        order_service.get_artwork_service.return_value = artwork_service

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sales_service.get_sale.return_value = None
        use_case.sales_service.create_sale.return_value = 42

        use_case.create_sales()

        # Verify confirm_sale was called after artwork
        use_case.sales_service.confirm_sale.assert_called_once_with(42)

    @patch("src.app.new_sale_use_case.logger")
    def test_create_sales_logs_order_processing(self, mock_logger, use_case, sample_order):
        """Test that create_sales logs order processing."""
        order_service = MagicMock(spec=IOrderService)
        order_service.get_orders.return_value = iter([sample_order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sales_service.get_sale.return_value = None
        use_case.sales_service.create_sale.return_value = 42

        use_case.create_sales()

        # Check for logging calls
        assert mock_logger.info.called
        assert mock_logger.error.call_count == 0


class TestNewSaleUseCaseIntegration:
    """Integration tests for NewSaleUseCase."""

    @pytest.fixture
    def use_case_dependencies(self):
        """Create mock dependencies for use case."""
        return {
            "order_services": MagicMock(spec=IRegistry),
            "artwork_services": MagicMock(spec=IRegistry),
            "sales_service": MagicMock(spec=ISalesService),
            "error_queue": MagicMock(spec=IErrorQueue),
            "open_orders_dir": Path("/tmp/orders"),
        }

    @pytest.fixture
    def use_case(self, use_case_dependencies):
        """Create a NewSaleUseCase instance."""
        return NewSaleUseCase(**use_case_dependencies)

    @pytest.fixture
    def sample_order(self):
        """Create a sample order."""
        return create_sample_order()

    def test_full_workflow_new_sale_creation(self, use_case, sample_order):
        """Test complete workflow for creating a new sale."""
        order_service = MagicMock(spec=IOrderService)
        order_service.get_orders.return_value = iter([sample_order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sales_service.get_sale.return_value = None
        use_case.sales_service.create_sale.return_value = 42

        use_case.create_sales()

        # Verify the complete flow
        assert sample_order.id == 42
        use_case.sales_service.create_sale.assert_called_once()
        use_case.sales_service.confirm_sale.assert_called_once_with(42)

    def test_full_workflow_existing_sale_update(self, use_case, sample_order):
        """Test complete workflow for updating an existing sale."""
        order_service = MagicMock(spec=IOrderService)
        order_service.get_orders.return_value = iter([sample_order])
        order_service.get_artwork_service.return_value = None

        use_case.order_services.items.return_value = [("test_service", order_service)]
        use_case.sales_service.get_sale.return_value = {"id": 99}
        use_case.sales_service.verify_sale_quantities.return_value = True

        use_case.create_sales()

        # Verify the complete flow
        assert sample_order.id == 99
        use_case.sales_service.update_contact.assert_called_once()
        # confirm_sale is called twice: once in create_or_update_sale, once after artwork
        assert use_case.sales_service.confirm_sale.call_count == 2
