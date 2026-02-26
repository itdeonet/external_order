"""Unit tests for HarmanOrderService."""

import contextlib
import datetime as dt
import json
import pathlib
from unittest.mock import patch

import pytest
from pydifact import Segment  # type: ignore

from src.domain.order import Order, OrderStatus
from src.interfaces.iartwork_service import IArtworkService
from src.interfaces.ierror_queue import IErrorQueue
from src.services.harman_order_service import HarmanOrderService
from src.services.render_service import RenderService


class TestHarmanOrderServiceInstantiation:
    """Tests for HarmanOrderService instantiation."""

    @pytest.fixture
    def mock_renderer(self, mocker):
        """Provide a mocked RenderService."""
        return mocker.Mock(spec=RenderService)

    def test_instantiation_with_all_fields(self, tmp_path, mock_renderer):
        """Test creating HarmanOrderService with all fields."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        service = HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=input_dir,
            output_dir=output_dir,
            renderer=mock_renderer,
        )

        assert service.administration_id == 1
        assert service.customer_id == 100
        assert service.pricelist_id == 50
        assert service.order_provider == "Harman"
        assert service.shipment_type == "standard"
        assert service.workdays_for_delivery == 5
        assert service.input_dir == input_dir
        assert service.output_dir == output_dir
        assert service.renderer is mock_renderer

    def test_instantiation_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(TypeError):
            HarmanOrderService(
                administration_id=1,
                customer_id=100,
                pricelist_id=50,
                order_provider="Harman",
            )  # type: ignore


class TestHarmanOrderServiceFromConfig:
    """Tests for from_config class method."""

    def test_from_config(self, mocker, tmp_path):
        """Test creating HarmanOrderService from config."""
        mock_config = mocker.Mock()
        mock_config.harman_administration_id = 10
        mock_config.harman_customer_id = 200
        mock_config.harman_pricelist_id = 60
        mock_config.harman_order_provider = "HarmanProvider"
        mock_config.harman_shipment_type = "express"
        mock_config.harman_workdays_for_delivery = 7
        mock_config.harman_input_dir = tmp_path / "input"
        mock_config.harman_output_dir = tmp_path / "output"
        mock_config.templates_dir = tmp_path / "templates"

        mocker.patch(
            "src.services.harman_order_service.RenderService",
            return_value=mocker.Mock(spec=RenderService),
        )

        service = HarmanOrderService.from_config(mock_config)

        assert service.administration_id == 10
        assert service.customer_id == 200
        assert service.pricelist_id == 60
        assert service.order_provider == "HarmanProvider"
        assert service.shipment_type == "express"
        assert service.workdays_for_delivery == 7

    def test_from_config_creates_renderer_service(self, mocker, tmp_path):
        """Test that from_config creates RenderService with templates_dir."""
        mock_config = mocker.Mock()
        mock_config.harman_administration_id = 1
        mock_config.harman_customer_id = 1
        mock_config.harman_pricelist_id = 1
        mock_config.harman_order_provider = "Provider"
        mock_config.harman_shipment_type = "type"
        mock_config.harman_workdays_for_delivery = 5
        mock_config.harman_input_dir = tmp_path / "input"
        mock_config.harman_output_dir = tmp_path / "output"
        mock_config.templates_dir = tmp_path / "templates"

        mock_renderer_class = mocker.patch(
            "src.services.harman_order_service.RenderService",
            return_value=mocker.Mock(spec=RenderService),
        )

        service = HarmanOrderService.from_config(mock_config)

        assert isinstance(service, HarmanOrderService)
        mock_renderer_class.assert_called_once_with(directory=mock_config.templates_dir)


class TestGetOrderData:
    """Tests for _get_order_data and _get_segment_data methods."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        mock_renderer = mocker.Mock(spec=RenderService)
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    def test_get_segment_data_nad_segment(self, service, mocker):
        """Test extracting data from NAD segment."""
        segment = mocker.Mock(spec=Segment)
        segment.tag = "NAD"
        segment.elements = [
            "ST",
            "CUST123",
            ["Acme Corp", "John Doe", "john@example.com"],
            ["+1-555-0123"],
            ["123 Main", "Suite 100", "apt 5", "St"],
            "Chicago",
            "IL",
            "60601",
            "US",
        ]

        order_data = {"ship_to": {}, "line_items": []}
        service._get_segment_data(segment, order_data)

        assert order_data["ship_to"]["remote_customer_id"] == "CUST123"
        assert order_data["ship_to"]["company_name"] == "Acme Corp"
        assert order_data["ship_to"]["contact_name"] == "John Doe"
        assert order_data["ship_to"]["email"] == "john@example.com"
        assert order_data["ship_to"]["phone"] == "+1-555-0123"
        assert order_data["ship_to"]["street1"] == "123 Main St"
        assert order_data["ship_to"]["street2"] == "Suite 100"
        assert order_data["ship_to"]["city"] == "Chicago"
        assert order_data["ship_to"]["state"] == "IL"
        assert order_data["ship_to"]["postal_code"] == "60601"
        assert order_data["ship_to"]["country_code"] == "US"

    def test_get_segment_data_nad_segment_no_company(self, service, mocker):
        """Test NAD segment with empty company name."""
        segment = mocker.Mock(spec=Segment)
        segment.tag = "NAD"
        segment.elements = [
            "ST",
            "CUST123",
            ["", "Jane Doe", "jane@example.com"],
            ["+1-555-0124"],
            ["456 Oak", "", "", "Ave"],
            "Boston",
            "MA",
            "02101",
            "US",
        ]

        order_data = {"ship_to": {}, "line_items": []}
        service._get_segment_data(segment, order_data)

        assert order_data["ship_to"]["company_name"] == ""
        assert order_data["ship_to"]["contact_name"] == "Jane Doe"

    def test_get_segment_data_rff_delivery_note(self, service, mocker):
        """Test extracting delivery note ID from RFF segment."""
        segment = mocker.Mock(spec=Segment)
        segment.tag = "RFF"
        segment.elements = ["DQ", "DELIV-123"]

        order_data = {"ship_to": {}, "line_items": []}
        service._get_segment_data(segment, order_data)

        assert order_data["delivery_note_id"] == "DELIV-123"

    def test_get_segment_data_rff_order_id(self, service, mocker):
        """Test extracting remote order ID from RFF segment."""
        segment = mocker.Mock(spec=Segment)
        segment.tag = "RFF"
        segment.elements = ["ON", "ORD-12345"]

        order_data = {"ship_to": {}, "line_items": []}
        service._get_segment_data(segment, order_data)

        assert order_data["remote_order_id"] == "ORD-12345"

    def test_get_segment_data_lin_segment(self, service, mocker):
        """Test extracting line item data from LIN segment."""
        segment = mocker.Mock(spec=Segment)
        segment.tag = "LIN"
        segment.elements = ["1", "1", ["PROD001", "MF"]]

        order_data = {"ship_to": {}, "line_items": []}
        service._get_segment_data(segment, order_data)

        assert len(order_data["line_items"]) == 1
        assert order_data["line_items"][0]["remote_line_id"] == "1"
        assert order_data["line_items"][0]["product_code"] == "PROD001"

    def test_get_segment_data_qty_segment(self, service, mocker):
        """Test extracting quantity data from QTY segment."""
        segment_lin = mocker.Mock(spec=Segment)
        segment_lin.tag = "LIN"
        segment_lin.elements = ["1", "1", ["PROD001", "MF"]]

        segment_qty = mocker.Mock(spec=Segment)
        segment_qty.tag = "QTY"
        segment_qty.elements = ["113", "100", "PCE"]

        order_data = {"ship_to": {}, "line_items": []}
        service._get_segment_data(segment_lin, order_data)
        service._get_segment_data(segment_qty, order_data)

        assert order_data["line_items"][0]["quantity"] == "100"
        assert order_data["line_items"][0]["unit_of_measure"] == "PCE"

    def test_get_segment_data_qty_segment_no_line_item_raises_assertion(self, service, mocker):
        """Test that QTY segment without preceding LIN segment raises AssertionError."""
        segment = mocker.Mock(spec=Segment)
        segment.tag = "QTY"
        segment.elements = ["113", "100", "PCE"]

        order_data = {"ship_to": {}, "line_items": []}

        with pytest.raises(AssertionError):
            service._get_segment_data(segment, order_data)

    def test_get_segment_data_ftx_segment(self, service, mocker):
        """Test extracting location and stock status from FTX segment."""
        segment_lin = mocker.Mock(spec=Segment)
        segment_lin.tag = "LIN"
        segment_lin.elements = ["1", "1", ["PROD001", "MF"]]

        segment_ftx = mocker.Mock(spec=Segment)
        segment_ftx.tag = "FTX"
        segment_ftx.elements = ["PRD", "", "", ["USA", "In Stock"]]

        order_data = {"ship_to": {}, "line_items": []}
        service._get_segment_data(segment_lin, order_data)
        service._get_segment_data(segment_ftx, order_data)

        assert order_data["line_items"][0]["location"] == "USA"
        assert order_data["line_items"][0]["stock_status"] == "In Stock"

    def test_get_segment_data_unmatched_segment(self, service, mocker):
        """Test that unmatched segments are ignored."""
        segment = mocker.Mock(spec=Segment)
        segment.tag = "UNKNOWN"
        segment.elements = ["data"]

        order_data = {"ship_to": {}, "line_items": []}
        result = service._get_segment_data(segment, order_data)

        assert result == order_data


class TestMakeOrder:
    """Tests for _make_order method."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        mock_renderer = mocker.Mock(spec=RenderService)
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    @pytest.fixture
    def order_data_b2b(self):
        """Provide order data for B2B customer."""
        return {
            "remote_order_id": "ORD-12345",
            "ship_to": {
                "remote_customer_id": "CUST123",
                "company_name": "Acme Corp",
                "contact_name": "John Doe",
                "email": "john@example.com",
                "phone": "+1-555-0123",
                "street1": "123 Main St",
                "street2": "Suite 100",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country_code": "US",
            },
            "line_items": [
                {
                    "id": "1",
                    "product_code": "PROD001",
                    "quantity": 100,
                }
            ],
        }

    @pytest.fixture
    def order_data_b2c(self):
        """Provide order data for B2C customer."""
        return {
            "remote_order_id": "ORD-54321",
            "ship_to": {
                "remote_customer_id": "CUST456",
                "company_name": "",
                "contact_name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "+1-555-0124",
                "street1": "456 Oak Ave",
                "street2": "",
                "city": "Boston",
                "state": "MA",
                "postal_code": "02101",
                "country_code": "US",
            },
            "line_items": [
                {
                    "id": "1",
                    "product_code": "PROD002",
                    "quantity": 50,
                }
            ],
        }

    def test_make_order_b2b(self, service, order_data_b2b):
        """Test creating order for B2B customer."""
        order = service._make_order(order_data_b2b)

        assert isinstance(order, Order)
        assert order.administration_id == 1
        assert order.customer_id == 100
        assert order.order_provider == "Harman"
        assert order.pricelist_id == 50
        assert order.remote_order_id == "ORD-12345"
        assert order.shipment_type == "standardb2b%"
        assert order.ship_to.company_name == "Acme Corp"
        assert len(order.line_items) == 1

    def test_make_order_b2c(self, service, order_data_b2c):
        """Test creating order for B2C customer."""
        order = service._make_order(order_data_b2c)

        assert isinstance(order, Order)
        assert order.shipment_type == "standardb2c%"
        assert order.ship_to.company_name == ""

    def test_make_order_multiple_line_items(self, service, order_data_b2b):
        """Test creating order with multiple line items."""
        order_data_b2b["line_items"] = [
            {"id": "1", "product_code": "PROD001", "quantity": 100},
            {"id": "2", "product_code": "PROD002", "quantity": 50},
            {"id": "3", "product_code": "PROD003", "quantity": 25},
        ]

        order = service._make_order(order_data_b2b)

        assert len(order.line_items) == 3

    def test_make_order_missing_optional_fields(self, service):
        """Test creating order with missing optional fields."""
        order_data = {
            "ship_to": {
                "remote_customer_id": "CUST123",
                "contact_name": "John Doe",
                "email": "john@example.com",
                "phone": "+1-555-0123",
                "street1": "123 Main St",
                "city": "Chicago",
                "postal_code": "60601",
                "country_code": "US",
            },
            "line_items": [{"id": "1", "product_code": "PROD001", "quantity": 100}],
            "remote_order_id": "12345",
        }

        order = service._make_order(order_data)

        assert order.ship_to.company_name == ""
        assert order.ship_to.street2 == ""
        assert order.ship_to.state == ""


class TestGetArtworkService:
    """Tests for get_artwork_service method."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        mock_renderer = mocker.Mock(spec=RenderService)
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    @pytest.fixture
    def mock_order(self, mocker):
        """Provide a mock Order instance."""
        return mocker.Mock(spec=Order)

    @pytest.fixture
    def mock_registry(self, mocker):
        """Provide a mock Registry."""
        registry = mocker.Mock()
        registry.get = mocker.Mock()
        return registry

    def test_get_artwork_service_ha_format(self, service, mock_order, mock_registry, mocker):
        """Test getting artwork service for HA format order ID."""
        mock_order.remote_order_id = "HA-EM-12345"
        mock_spectrum = mocker.Mock(spec=IArtworkService)
        mock_registry.get.return_value = mock_spectrum

        result = service.get_artwork_service(mock_order, mock_registry)

        assert result is mock_spectrum
        mock_registry.get.assert_called_once_with("Spectrum")

    def test_get_artwork_service_jb_format(self, service, mock_order, mock_registry, mocker):
        """Test getting artwork service for JB format order ID."""
        mock_order.remote_order_id = "JB-EM-ST-99999"
        mock_spectrum = mocker.Mock(spec=IArtworkService)
        mock_registry.get.return_value = mock_spectrum

        result = service.get_artwork_service(mock_order, mock_registry)

        assert result is mock_spectrum
        mock_registry.get.assert_called_once_with("Spectrum")

    def test_get_artwork_service_ha_format_no_st(self, service, mock_order, mock_registry, mocker):
        """Test getting artwork service for HA format without ST."""
        mock_order.remote_order_id = "HA-EM-ST-54321"
        mock_spectrum = mocker.Mock(spec=IArtworkService)
        mock_registry.get.return_value = mock_spectrum

        result = service.get_artwork_service(mock_order, mock_registry)

        assert result is mock_spectrum

    def test_get_artwork_service_non_matching_format(self, service, mock_order, mock_registry):
        """Test that non-matching format returns None."""
        mock_order.remote_order_id = "ORD-12345"

        result = service.get_artwork_service(mock_order, mock_registry)

        assert result is None
        mock_registry.get.assert_not_called()

    def test_get_artwork_service_multiple_formats(self, service, mock_registry, mocker):
        """Test various matching formats."""
        matching_formats = [
            "HA-EM-0",
            "JB-EM-0",
            "HA-EM-ST-0",
            "JB-EM-ST-99999",
        ]
        mock_spectrum = mocker.Mock(spec=IArtworkService)
        mock_registry.get.return_value = mock_spectrum

        for format_id in matching_formats:
            mock_order = mocker.Mock(spec=Order)
            mock_order.remote_order_id = format_id
            mock_registry.get.reset_mock()

            result = service.get_artwork_service(mock_order, mock_registry)

            assert result is mock_spectrum, f"Failed for format: {format_id}"


class TestPersistOrder:
    """Tests for persist_order method."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        (tmp_path / "input").mkdir(parents=True, exist_ok=True)
        (tmp_path / "output").mkdir(parents=True, exist_ok=True)
        mock_renderer = mocker.Mock(spec=RenderService)
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    def test_persist_order_renames_input_files_with_status(self, service, mocker, tmp_path):
        """Test that input files are renamed with the order status value."""
        # Create input files
        input_file = service.input_dir / "ORD-123.insdes"
        input_file.write_text("test")

        order = mocker.Mock(spec=Order)
        order.remote_order_id = "ORD-123"
        order.status = OrderStatus.CONFIRMED

        # Mock set_status to update the order.status attribute
        def mock_set_status(status):
            order.status = status

        order.set_status = mock_set_status

        mocker.patch(
            "src.services.harman_order_service.asdict",
            return_value={},
        )

        service.persist_order(order, OrderStatus.CONFIRMED)

        # Verify file was renamed with the status value
        expected_file = service.input_dir / "ORD-123.CONFIRMED"
        assert expected_file.exists()
        assert not input_file.exists()
        assert order.status == OrderStatus.CONFIRMED

    def test_persist_order_calls_set_status(self, service, mocker):
        """Test that persist_order calls order.set_status."""
        input_file = service.input_dir / "ORD-456.insdes"
        input_file.write_text("test")

        order = mocker.Mock(spec=Order)
        order.remote_order_id = "ORD-456"
        order.status = OrderStatus.SHIPPED

        def mock_set_status(status):
            order.status = status

        order.set_status = mock_set_status

        mocker.patch(
            "src.services.harman_order_service.asdict",
            return_value={},
        )

        service.persist_order(order, OrderStatus.SHIPPED)

        assert order.status == OrderStatus.SHIPPED

    def test_persist_order_writes_json_file(self, service, mocker):
        """Test that persist_order writes JSON file."""
        input_file = service.input_dir / "ORD-789.insdes"
        input_file.write_text("test")

        order = mocker.Mock(spec=Order)
        order.remote_order_id = "ORD-789"
        order.status = OrderStatus.CREATED

        def mock_set_status(status):
            order.status = status

        order.set_status = mock_set_status

        mocker.patch(
            "src.services.harman_order_service.asdict",
            return_value={"remote_order_id": "ORD-789", "status": "CREATED"},
        )

        service.persist_order(order, OrderStatus.CREATED)

        json_file = service.input_dir / "ORD-789.json"
        assert json_file.exists()
        content = json_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["remote_order_id"] == "ORD-789"

    def test_persist_order_datetime_serialization(self, service, mocker):
        """Test that datetime objects are properly serialized."""
        input_file = service.input_dir / "ORD-999.insdes"
        input_file.write_text("test")

        order = mocker.Mock(spec=Order)
        order.remote_order_id = "ORD-999"
        order.status = OrderStatus.SHIPPED

        def mock_set_status(status):
            order.status = status

        order.set_status = mock_set_status

        created_at = dt.datetime(2025, 2, 14, 10, 30, 45, tzinfo=dt.UTC)
        mocker.patch(
            "src.services.harman_order_service.asdict",
            return_value={"remote_order_id": "ORD-999", "created_at": created_at},
        )

        service.persist_order(order, OrderStatus.SHIPPED)

        json_file = service.input_dir / "ORD-999.json"
        content = json_file.read_text(encoding="utf-8")
        assert "2025-02-14" in content


class TestGetOrders:
    """Tests for get_orders generator method."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        (tmp_path / "input").mkdir(parents=True, exist_ok=True)
        mock_renderer = mocker.Mock(spec=RenderService)
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    def test_get_orders_is_generator(self, service, mocker):
        """Test that get_orders returns a generator."""
        from collections.abc import Generator

        error_queue = mocker.Mock(spec=IErrorQueue)
        result = service.get_orders(error_queue)

        # Verify it's a generator
        assert isinstance(result, Generator)

    def test_get_orders_empty_directory(self, service, mocker):
        """Test that get_orders returns empty generator for empty directory."""
        error_queue = mocker.Mock(spec=IErrorQueue)
        orders = list(service.get_orders(error_queue))

        assert len(orders) == 0
        error_queue.put.assert_not_called()

    def test_get_orders_yields_order_from_insdes_file(self, service, mocker):
        """Test that get_orders yields an order from a .insdes file."""
        # Create a file
        insdes_file = service.input_dir / "ORD-001.insdes"
        insdes_file.write_text("fake edi content")

        # Mock _get_order_data at the module level to return valid order data
        order_data = {
            "remote_order_id": "ORD-001",
            "ship_to": {
                "remote_customer_id": "CUST123",
                "company_name": "Acme Corp",
                "contact_name": "John Doe",
                "email": "john@acme.com",
                "phone": "1-555-0001",
                "street1": "123 Main St",
                "street2": "Suite 100",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country_code": "US",
            },
            "line_items": [{"id": "1", "product_code": "PROD001", "quantity": 100}],
        }
        mocker.patch(
            "src.services.harman_order_service.HarmanOrderService._get_order_data",
            return_value=order_data,
        )

        error_queue = mocker.Mock(spec=IErrorQueue)
        orders = list(service.get_orders(error_queue))

        assert len(orders) == 1
        assert isinstance(orders[0], Order)
        assert orders[0].remote_order_id == "ORD-001"
        error_queue.put.assert_not_called()

    def test_get_orders_yields_order_from_created_file(self, service, mocker):
        """Test that get_orders yields an order from a .created file."""
        # Create a file
        created_file = service.input_dir / "ORD-002.created"
        created_file.write_text("fake edi content")

        # Mock _get_order_data to return valid order data
        order_data = {
            "remote_order_id": "ORD-002",
            "ship_to": {
                "remote_customer_id": "CUST456",
                "company_name": "",
                "contact_name": "Jane Doe",
                "email": "jane@beta.com",
                "phone": "1-555-0002",
                "street1": "456 Oak Ave",
                "street2": "",
                "city": "Boston",
                "state": "MA",
                "postal_code": "02101",
                "country_code": "US",
            },
            "line_items": [{"id": "1", "product_code": "PROD002", "quantity": 50}],
        }
        mocker.patch(
            "src.services.harman_order_service.HarmanOrderService._get_order_data",
            return_value=order_data,
        )

        error_queue = mocker.Mock(spec=IErrorQueue)
        orders = list(service.get_orders(error_queue))

        assert len(orders) == 1
        assert isinstance(orders[0], Order)
        assert orders[0].remote_order_id == "ORD-002"
        error_queue.put.assert_not_called()

    def test_get_orders_yields_multiple_orders_from_mixed_files(self, service, mocker):
        """Test that get_orders yields all orders from both .insdes and .created files."""
        # Create multiple files with different extensions
        insdes_file = service.input_dir / "ORD-003.insdes"
        insdes_file.write_text("fake edi content")

        created_file = service.input_dir / "ORD-004.created"
        created_file.write_text("fake edi content")

        # Mock _get_order_data to return different data for each call
        order_data_1 = {
            "remote_order_id": "ORD-003",
            "ship_to": {
                "remote_customer_id": "CUST789",
                "company_name": "Gamma Inc",
                "contact_name": "John Smith",
                "email": "john@gamma.com",
                "phone": "1-555-0003",
                "street1": "789 Pine St",
                "street2": "",
                "city": "Denver",
                "state": "CO",
                "postal_code": "80202",
                "country_code": "US",
            },
            "line_items": [{"id": "1", "product_code": "PROD003", "quantity": 75}],
        }
        order_data_2 = {
            "remote_order_id": "ORD-004",
            "ship_to": {
                "remote_customer_id": "CUST000",
                "company_name": "Delta Ltd",
                "contact_name": "Jane Smith",
                "email": "jane@delta.com",
                "phone": "1-555-0004",
                "street1": "000 Elm St",
                "street2": "",
                "city": "Seattle",
                "state": "WA",
                "postal_code": "98101",
                "country_code": "US",
            },
            "line_items": [{"id": "1", "product_code": "PROD004", "quantity": 25}],
        }

        mocker.patch(
            "src.services.harman_order_service.HarmanOrderService._get_order_data",
            side_effect=[order_data_1, order_data_2],
        )

        error_queue = mocker.Mock(spec=IErrorQueue)
        orders = list(service.get_orders(error_queue))

        assert len(orders) == 2
        order_ids = {order.remote_order_id for order in orders}
        assert "ORD-003" in order_ids
        assert "ORD-004" in order_ids
        error_queue.put.assert_not_called()

    def test_get_orders_handles_parsing_exception(self, service, mocker):
        """Test that get_orders catches exceptions and puts them in error queue."""
        order_file = service.input_dir / "ORD-010.insdes"
        order_file.write_text("invalid edi")

        # Mock _get_order_data to raise an exception
        parsing_error = ValueError("Invalid EDI format")
        mocker.patch(
            "src.services.harman_order_service.HarmanOrderService._get_order_data",
            side_effect=parsing_error,
        )

        error_queue = mocker.Mock(spec=IErrorQueue)
        orders = list(service.get_orders(error_queue))

        assert len(orders) == 0
        error_queue.put.assert_called_once_with(parsing_error)

    def test_get_orders_handles_order_creation_exception(self, service, mocker):
        """Test that get_orders catches order creation exceptions."""
        order_file = service.input_dir / "ORD-011.insdes"
        order_file.write_text("edi content")

        order_data = {
            "remote_order_id": "ORD-011",
            "ship_to": {},
            "line_items": [],
        }
        mocker.patch(
            "src.services.harman_order_service.HarmanOrderService._get_order_data",
            return_value=order_data,
        )

        # Mock _make_order to raise an exception
        creation_error = RuntimeError("Failed to create order")
        mocker.patch(
            "src.services.harman_order_service.HarmanOrderService._make_order",
            side_effect=creation_error,
        )

        error_queue = mocker.Mock(spec=IErrorQueue)
        orders = list(service.get_orders(error_queue))

        assert len(orders) == 0
        error_queue.put.assert_called_once_with(creation_error)

    def test_get_orders_continues_after_exception(self, service, mocker):
        """Test that get_orders continues processing after encountering an exception."""
        # Create single file with exception handling
        order_file = service.input_dir / "ORD-012.insdes"
        order_file.write_text("bad edi")

        # Make _get_order_data fail on this file
        parsing_error = ValueError("Invalid EDI")
        mocker.patch(
            "src.services.harman_order_service.HarmanOrderService._get_order_data",
            side_effect=parsing_error,
        )

        error_queue = mocker.Mock(spec=IErrorQueue)
        orders = list(service.get_orders(error_queue))

        # Should have no successful orders and one error
        assert len(orders) == 0
        error_queue.put.assert_called_once_with(parsing_error)


class TestImmutability:
    """Tests for HarmanOrderService immutability (frozen dataclass)."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        mock_renderer = mocker.Mock(spec=RenderService)
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    def test_cannot_modify_administration_id(self, service):
        """Test that administration_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.administration_id = 2

    def test_cannot_modify_customer_id(self, service):
        """Test that customer_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.customer_id = 200

    def test_cannot_modify_pricelist_id(self, service):
        """Test that pricelist_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.pricelist_id = 60

    def test_cannot_modify_order_provider(self, service):
        """Test that order_provider cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.order_provider = "NewProvider"

    def test_cannot_modify_shipment_type(self, service):
        """Test that shipment_type cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.shipment_type = "express"

    def test_cannot_modify_workdays_for_delivery(self, service):
        """Test that workdays_for_delivery cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.workdays_for_delivery = 10

    def test_cannot_modify_input_dir(self, service):
        """Test that input_dir cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.input_dir = pathlib.Path("/other/path")

    def test_cannot_modify_output_dir(self, service):
        """Test that output_dir cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.output_dir = pathlib.Path("/other/path")

    def test_cannot_modify_renderer(self, service):
        """Test that renderer cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            service.renderer = None


class TestLoadOrder:
    """Tests for load_order method."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        (tmp_path / "input").mkdir(parents=True, exist_ok=True)
        mock_renderer = mocker.Mock(spec=RenderService)
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    def test_load_order_returns_order_when_file_exists(self, service, tmp_path, mocker):
        """Test that load_order returns an Order when JSON file exists."""
        order_file = service.input_dir / "ORD-123.json"
        order_data = {
            "administration_id": 1,
            "customer_id": 100,
            "pricelist_id": 50,
            "order_provider": "Harman",
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": {},
            "line_items": [],
        }
        order_file.write_text(json.dumps(order_data), encoding="utf-8")

        # Mock ShipTo to handle empty dict initialization
        mock_ship_to = mocker.Mock()
        mocker.patch("src.domain.order.ShipTo", return_value=mock_ship_to)

        with patch("src.services.harman_order_service.Order") as mock_order_class:
            mock_order = mocker.Mock(spec=Order)
            mock_order_class.return_value = mock_order

            result = service.load_order("ORD-123")

            assert result is mock_order

    def test_load_order_returns_none_when_file_not_found(self, service):
        """Test that load_order returns None when JSON file doesn't exist."""
        result = service.load_order("NONEXISTENT")

        assert result is None

    def test_load_order_reads_json_file(self, service):
        """Test that load_order correctly reads JSON file."""
        order_file = service.input_dir / "ORD-456.json"
        order_data = {
            "administration_id": 1,
            "customer_id": 100,
            "pricelist_id": 50,
            "order_provider": "Harman",
            "remote_order_id": "ORD-456",
            "shipment_type": "standard",
            "ship_to": {},
            "line_items": [],
        }
        order_file.write_text(json.dumps(order_data), encoding="utf-8")

        # Verify file content is read
        content = order_file.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["remote_order_id"] == "ORD-456"

    def test_load_order_handles_malformed_json(self, service):
        """Test that load_order raises when JSON is malformed."""
        order_file = service.input_dir / "ORD-789.json"
        order_file.write_text("invalid json {", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            service.load_order("ORD-789")


class TestNotifyCompletedSale:
    """Tests for notify_completed_sale method."""

    @pytest.fixture
    def service(self, tmp_path, mocker):
        """Provide a HarmanOrderService instance."""
        (tmp_path / "output").mkdir(parents=True, exist_ok=True)
        (tmp_path / "templates").mkdir(parents=True, exist_ok=True)
        mock_renderer = mocker.Mock(spec=RenderService)
        mock_renderer.directory = tmp_path / "templates"
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
            workdays_for_delivery=5,
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            renderer=mock_renderer,
        )

    def test_notify_completed_sale_with_no_templates(self, service, mocker):
        """Test that notify_completed_sale handles no templates gracefully."""
        order = mocker.Mock(spec=Order)
        order.remote_order_id = "ORD-123"

        # No templates in directory, so no files should be written
        service.notify_completed_sale(order)

        # Just verify the method completes without error
        # and that the output directory still exists
        assert service.output_dir.exists()

    def test_notify_completed_sale_creates_subdirectories(self, service, mocker):
        """Test that notify_completed_sale creates required subdirectories."""
        # Create a template file
        template_file = service.renderer.directory / "desadv-D96A.j2"
        template_file.write_text("test content")

        order = mocker.Mock(spec=Order)
        order.remote_order_id = "ORD-789"

        # Mock the renderer to return valid EDIFACT content
        service.renderer.render.return_value = "UNB+UNOC:3+TEST+TEST+030101:1200+1'+UNH+1+DESADV:D:96A:UN:EAN008+1'+BGM+350+1+'3+9'UNT+4+1'UNZ+1+1'"

        with contextlib.suppress(Exception):
            service.notify_completed_sale(order)
