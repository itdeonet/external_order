"""Unit tests for HarmanOrderService."""

import datetime as dt
import pathlib

from pydifact import Segment  # type: ignore
import pytest

from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.order import Order
from src.services.harman_order_service import HarmanOrderService


class TestHarmanOrderServiceInstantiation:
    """Tests for HarmanOrderService instantiation."""

    def test_instantiation_with_all_fields(self):
        """Test creating HarmanOrderService with all fields."""
        service = HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
        )

        assert service.administration_id == 1
        assert service.customer_id == 100
        assert service.pricelist_id == 50
        assert service.order_provider == "Harman"
        assert service.shipment_type == "standard"

    def test_instantiation_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(TypeError):
            HarmanOrderService(
                administration_id=1,
                customer_id=100,
                pricelist_id=50,
                order_provider="Harman",
            )  # type: ignore


class TestHarmanOrderServiceFromSettings:
    """Tests for from_settings class method."""

    def test_from_settings(self, mocker):
        """Test creating HarmanOrderService from settings."""
        mock_settings = mocker.Mock()
        mock_settings.harman_administration_id = 10
        mock_settings.harman_customer_id = 200
        mock_settings.harman_pricelist_id = 60
        mock_settings.harman_order_provider = "HarmanProvider"
        mock_settings.harman_shipment_type = "express"

        mocker.patch(
            "src.services.harman_order_service.get_settings",
            return_value=mock_settings,
        )

        service = HarmanOrderService.from_settings()

        assert service.administration_id == 10
        assert service.customer_id == 200
        assert service.pricelist_id == 60
        assert service.order_provider == "HarmanProvider"
        assert service.shipment_type == "express"

    def test_from_settings_calls_get_settings(self, mocker):
        """Test that from_settings calls get_settings."""
        mock_settings = mocker.Mock()
        mock_settings.harman_administration_id = 1
        mock_settings.harman_customer_id = 1
        mock_settings.harman_pricelist_id = 1
        mock_settings.harman_order_provider = "Provider"
        mock_settings.harman_shipment_type = "type"

        mock_get_settings = mocker.patch(
            "src.services.harman_order_service.get_settings",
            return_value=mock_settings,
        )

        HarmanOrderService.from_settings()
        mock_get_settings.assert_called_once()


class TestHarmanOrderServiceGetSegmentData:
    """Tests for _get_segment_data method."""

    @pytest.fixture
    def service(self):
        """Provide a HarmanOrderService instance."""
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
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
        assert order_data["line_items"][0]["id"] == "1"
        assert order_data["line_items"][0]["product_id"] == "PROD001"

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


class TestHarmanOrderServiceMakeOrder:
    """Tests for _make_order method."""

    @pytest.fixture
    def service(self):
        """Provide a HarmanOrderService instance."""
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
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
                    "product_id": "PROD001",
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
                    "product_id": "PROD002",
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
            {"id": "1", "product_id": "PROD001", "quantity": 100},
            {"id": "2", "product_id": "PROD002", "quantity": 50},
            {"id": "3", "product_id": "PROD003", "quantity": 25},
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
            "line_items": [{"id": "1", "product_id": "PROD001", "quantity": 100}],
            "remote_order_id": "12345",
        }

        order = service._make_order(order_data)

        assert order.ship_to.company_name == ""
        assert order.ship_to.street2 == ""
        assert order.ship_to.state == ""


class TestHarmanOrderServiceGetArtworkService:
    """Tests for get_artwork_service method."""

    @pytest.fixture
    def service(self):
        """Provide a HarmanOrderService instance."""
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
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

    def test_get_artwork_service_partial_match(self, service, mock_order, mock_registry):
        """Test that partial matches don't return artwork service."""
        mock_order.remote_order_id = "HA-XX-12345"

        result = service.get_artwork_service(mock_order, mock_registry)

        assert result is None

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


class TestHarmanOrderServiceSaveOrder:
    """Tests for save_order method."""

    @pytest.fixture
    def service(self):
        """Provide a HarmanOrderService instance."""
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
        )

    @pytest.fixture
    def mock_order_with_id(self, mocker):
        """Provide a mock Order with ID set."""
        order = mocker.Mock(spec=Order)
        order.id = 12345
        order.remote_order_id = "ORD-123"
        order.administration_id = 1
        order.customer_id = 100
        order.order_provider = "Harman"
        order.pricelist_id = 50
        return order

    @pytest.fixture
    def mock_order_without_id(self, mocker):
        """Provide a mock Order without ID."""
        order = mocker.Mock(spec=Order)
        order.id = 0
        order.remote_order_id = "ORD-456"
        order.administration_id = 1
        order.customer_id = 100
        order.order_provider = "Harman"
        order.pricelist_id = 50
        return order

    def test_save_order_with_id(self, service, mock_order_with_id, mocker, tmp_path):
        """Test saving order with ID set."""
        mocker.patch("src.domain.interfaces.iorder_service.asdict", return_value={})
        spy = mocker.spy(pathlib.Path, "write_text")
        service.save_order(mock_order_with_id, tmp_path)
        file_path = tmp_path / f"S{mock_order_with_id.id}.json"
        spy.assert_called_once_with(file_path, "{}", encoding="utf-8")

    def test_save_order_without_id(self, service, mock_order_without_id, mocker, tmp_path):
        """Test saving order without ID."""
        mocker.patch("src.domain.interfaces.iorder_service.asdict", return_value={})
        spy = mocker.spy(pathlib.Path, "write_text")
        service.save_order(mock_order_without_id, tmp_path)
        spy.assert_called_once()

    def test_save_order_json_format(self, service, mock_order_with_id, mocker, tmp_path):
        """Test that order is saved as properly formatted JSON."""
        mock_order_with_id.id = 12345
        mocker.patch(
            "src.domain.interfaces.iorder_service.asdict",
            return_value={"id": 12345, "remote_order_id": "ORD-123"},
        )

        spy = mocker.spy(pathlib.Path, "write_text")
        service.save_order(mock_order_with_id, tmp_path)
        spy.assert_called_once()

        written_content = spy.call_args[0][1]
        assert isinstance(written_content, str)
        assert "12345" in written_content

    def test_save_order_datetime_serialization(self, service, mocker, tmp_path):
        """Test that datetime objects are properly serialized."""
        order = mocker.Mock(spec=Order)
        order.id = 100
        created_at = dt.datetime(2025, 2, 14, 10, 30, 45, tzinfo=dt.UTC)
        mocker.patch(
            "src.domain.interfaces.iorder_service.asdict",
            return_value={"id": 100, "created_at": created_at},
        )

        spy = mocker.spy(pathlib.Path, "write_text")
        service.save_order(order, tmp_path)
        written_content = spy.call_args[0][1]
        assert "2025-02-14" in written_content


class TestHarmanOrderServiceGetOrders:
    """Tests for get_orders method."""

    @pytest.fixture
    def service(self):
        """Provide a HarmanOrderService instance."""
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
        )

    def test_get_orders_generates_orders(self, service, mocker, tmp_path):
        """Test that get_orders generates Order instances."""
        # Create a test file
        test_file = tmp_path / "test.insdes"
        test_file.write_text("test content")

        # Mock the Parser
        mock_segment1 = mocker.Mock(spec=Segment)
        mock_segment1.tag = "RFF"
        mock_segment1.elements = ["ON", "ORD-12345"]

        mock_segment2 = mocker.Mock(spec=Segment)
        mock_segment2.tag = "NAD"
        mock_segment2.elements = [
            "ST",
            "CUST123",
            ["Acme", "John", "john@example.com"],
            ["555-0123"],
            ["123 Main", "", "", "St"],
            "Chicago",
            "IL",
            "60601",
            "US",
        ]

        mock_segment3 = mocker.Mock(spec=Segment)
        mock_segment3.tag = "LIN"
        mock_segment3.elements = ["1", "1", ["PROD001", "MF"]]

        mock_segment4 = mocker.Mock(spec=Segment)
        mock_segment4.tag = "QTY"
        mock_segment4.elements = ["113", "100", "PCE"]

        mock_parser = mocker.Mock()
        mock_parser.parse.return_value = [
            mock_segment1,
            mock_segment2,
            mock_segment3,
            mock_segment4,
        ]

        mocker.patch(
            "src.services.harman_order_service.Parser",
            return_value=mock_parser,
        )

        mock_error_queue = mocker.Mock(spec=["put"])
        orders = list(service.get_orders(tmp_path, mock_error_queue))

        assert len(orders) == 1
        assert isinstance(orders[0], Order)

    def test_get_orders_multiple_files(self, service, mocker, tmp_path):
        """Test that get_orders processes multiple files."""
        # Create test files
        test_files = [
            tmp_path / "test1.insdes",
            tmp_path / "test2.insdes",
            tmp_path / "test3.insdes",
        ]
        for f in test_files:
            f.write_text("test content")

        # Mock segments for each file
        mock_segments_template = [
            mocker.Mock(spec=Segment, tag="RFF", elements=["ON", "ORD-00001"]),
            mocker.Mock(
                spec=Segment,
                tag="NAD",
                elements=[
                    "ST",
                    "CUST",
                    ["Corp", "John", "john@example.com"],
                    ["555-0123"],
                    ["123 Main", "", "", "St"],
                    "City",
                    "ST",
                    "12345",
                    "US",
                ],
            ),
            mocker.Mock(spec=Segment, tag="LIN", elements=["1", "1", ["PROD", "MF"]]),
            mocker.Mock(spec=Segment, tag="QTY", elements=["113", "100", "PCE"]),
        ]

        mock_parser = mocker.Mock()
        # Set different remote order IDs for each call
        mock_parser.parse.side_effect = [
            [*mock_segments_template],
            [*mock_segments_template],
            [*mock_segments_template],
        ]

        mocker.patch(
            "src.services.harman_order_service.Parser",
            return_value=mock_parser,
        )

        mock_error_queue = mocker.Mock(spec=["put"])
        orders = list(service.get_orders(tmp_path, mock_error_queue))

        assert len(orders) == 3

    def test_get_orders_handles_exception(self, service, mocker, tmp_path):
        """Test that exceptions are put in error queue."""
        test_file = tmp_path / "test.insdes"
        test_file.write_text("test content")

        mock_parser = mocker.Mock()
        mock_parser.parse.side_effect = ValueError("Parse error")

        mocker.patch(
            "src.services.harman_order_service.Parser",
            return_value=mock_parser,
        )

        mock_error_queue = mocker.Mock(spec=["put"])
        orders = list(service.get_orders(tmp_path, mock_error_queue))

        assert len(orders) == 0
        mock_error_queue.put.assert_called_once()
        assert isinstance(mock_error_queue.put.call_args[0][0], ValueError)

    def test_get_orders_case_insensitive_glob(self, service, mocker, tmp_path):
        """Test that file globbing is case insensitive."""
        # Create files with different cases
        test_files = [
            tmp_path / "test.INSDES",
            tmp_path / "test2.Insdes",
            tmp_path / "test3.insdes",
        ]
        for f in test_files:
            f.write_text("test content")

        mock_segments = [
            mocker.Mock(spec=Segment, tag="RFF", elements=["ON", "ORD"]),
            mocker.Mock(
                spec=Segment,
                tag="NAD",
                elements=[
                    "ST",
                    "CUST",
                    ["Corp", "John", "john@example.com"],
                    ["555-0123"],
                    ["123 Main", "", "", "St"],
                    "City",
                    "ST",
                    "12345",
                    "US",
                ],
            ),
            mocker.Mock(spec=Segment, tag="LIN", elements=["1", "1", ["PROD", "MF"]]),
            mocker.Mock(spec=Segment, tag="QTY", elements=["113", "100", "PCE"]),
        ]

        mock_parser = mocker.Mock()
        mock_parser.parse.return_value = mock_segments

        mocker.patch(
            "src.services.harman_order_service.Parser",
            return_value=mock_parser,
        )

        mock_error_queue = mocker.Mock(spec=["put"])
        orders = list(service.get_orders(tmp_path, mock_error_queue))

        assert len(orders) == 3

    def test_get_orders_is_generator(self, service, mocker, tmp_path):
        """Test that get_orders returns a generator."""
        test_file = tmp_path / "test.insdes"
        test_file.write_text("test content")

        mock_parser = mocker.Mock()
        mock_parser.parse.return_value = [
            mocker.Mock(spec=Segment, tag="RFF", elements=["ON", "ORD"]),
            mocker.Mock(
                spec=Segment,
                tag="NAD",
                elements=[
                    "ST",
                    "CUST",
                    ["Corp", "John", "john@example.com"],
                    ["555-0123"],
                    ["123 Main", "", "", "St"],
                    "City",
                    "ST",
                    "12345",
                    "US",
                ],
            ),
            mocker.Mock(spec=Segment, tag="LIN", elements=["1", "1", ["PROD", "MF"]]),
            mocker.Mock(spec=Segment, tag="QTY", elements=["113", "100", "PCE"]),
        ]

        mocker.patch(
            "src.services.harman_order_service.Parser",
            return_value=mock_parser,
        )

        mock_error_queue = mocker.Mock(spec=["put"])
        result = service.get_orders(tmp_path, mock_error_queue)

        from collections.abc import Generator

        assert isinstance(result, Generator)


class TestHarmanOrderServiceImmutability:
    """Tests for HarmanOrderService immutability (frozen dataclass)."""

    @pytest.fixture
    def service(self):
        """Provide a HarmanOrderService instance."""
        return HarmanOrderService(
            administration_id=1,
            customer_id=100,
            pricelist_id=50,
            order_provider="Harman",
            shipment_type="standard",
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
