"""Unit tests for CamelbakOrderService."""

import datetime as dt
import json
from unittest.mock import Mock

import pytest
import requests

from src.config import get_config
from src.domain import IArtworkService, Order, OrderStatus
from src.services.spectrum_order_service import SpectrumOrderService


@pytest.fixture
def mock_session(mocker):
    """Provide a mocked requests.Session."""
    mock = mocker.Mock(spec=requests.Session)
    mock.headers = {}
    return mock


@pytest.fixture
def mock_artwork_service():
    """Provide a mocked IArtworkService."""
    mock = Mock(spec=IArtworkService)
    return mock


class TestSpectrumOrderServiceInstantiation:
    """Tests for SpectrumOrderService instantiation."""

    def test_instantiation_with_required_fields(self, mock_session, mock_artwork_service):
        """Test creating SpectrumOrderService with required fields."""
        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
        )

        assert service.session is mock_session
        assert service.artwork_service is mock_artwork_service

    def test_instantiation_with_defaults(self, mock_session, mock_artwork_service):
        """Test creating SpectrumOrderService with default values from config."""
        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
        )

        assert service.session is mock_session
        assert service.artwork_service is mock_artwork_service
        assert service.base_url == get_config().spectrum_base_url
        assert service.administration_id == get_config().camelbak_administration_id
        assert service.customer_id == get_config().camelbak_customer_id
        assert service.pricelist_id == get_config().camelbak_pricelist_id
        assert service.order_provider == get_config().camelbak_order_provider
        assert service.shipment_type == get_config().camelbak_shipment_type
        assert service.workdays_for_delivery == get_config().camelbak_workdays_for_delivery

    def test_instantiation_with_custom_values(self, tmp_path, mock_session, mock_artwork_service):
        """Test creating SpectrumOrderService with custom values."""
        input_dir = tmp_path / "input"
        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            base_url="http://custom.example.com",
            administration_id=10,
            customer_id=200,
            pricelist_id=5,
            order_provider="CustomProvider",
            shipment_type="custom%",
            workdays_for_delivery=7,
            input_dir=input_dir,
        )

        assert service.session is mock_session
        assert service.artwork_service is mock_artwork_service
        assert service.base_url == "http://custom.example.com"
        assert service.administration_id == 10
        assert service.customer_id == 200
        assert service.pricelist_id == 5
        assert service.order_provider == "CustomProvider"
        assert service.shipment_type == "custom%"
        assert service.workdays_for_delivery == 7
        assert service.input_dir == input_dir

    def test_register_classmethod_creates_instance_with_defaults(self, mock_session, mocker):
        """Test that register() classmethod creates instance with config defaults."""
        mock_artwork_service = Mock(spec=IArtworkService)
        mock_registry = Mock()
        mock_order_registry = Mock()

        mocker.patch(
            "src.services.spectrum_order_service.get_artwork_services",
            return_value=mock_registry,
        )
        mocker.patch(
            "src.services.spectrum_order_service.get_order_services",
            return_value=mock_order_registry,
        )
        mock_registry.get.return_value = mock_artwork_service

        SpectrumOrderService.register(
            "spectrum_orders", mock_session, "test-api-key", "spectrum_artwork"
        )

        # Verify headers were updated with API key
        assert mock_session.headers.get("SPECTRUM_API_TOKEN") == "test-api-key"

        # Verify artwork service was retrieved from registry
        mock_registry.get.assert_called_once_with("spectrum_artwork")

        # Verify register was called
        mock_order_registry.register.assert_called_once()
        call_args = mock_order_registry.register.call_args
        assert call_args[0][0] == "spectrum_orders"
        assert isinstance(call_args[0][1], SpectrumOrderService)

    def test_register_classmethod_raises_when_artwork_provider_not_found(
        self, mock_session, mocker
    ):
        """Test that register() raises error when artwork provider not found."""
        mock_registry = Mock()
        mocker.patch(
            "src.services.spectrum_order_service.get_artwork_services",
            return_value=mock_registry,
        )
        mock_registry.get.return_value = None

        with pytest.raises(ValueError, match="Artwork service .* not found in registry"):
            SpectrumOrderService.register(
                "spectrum_orders", mock_session, "test-api-key", "nonexistent_artwork"
            )


class TestReadOrders:
    """Tests for read_orders generator method."""

    def test_read_orders_is_generator(self, mock_session, mock_artwork_service):
        """Test that read_orders returns a generator."""
        from collections.abc import Generator

        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
        )
        result = service.read_orders()

        assert isinstance(result, Generator)

    def test_read_orders_yields_orders_from_api(self, mock_session, mock_artwork_service, mocker):
        """Test that read_orders calls API and yields Order instances."""
        api_response = [
            {
                "purchaseOrderNumber": "ORDER-001",
                "userId": "USER123",
                "emailAddress": "user@example.com",
                "phoneNumber": "+1-555-0001",
                "shippingAddress": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "address1": "123 Main St",
                    "address2": "Suite 100",
                    "city": "Chicago",
                    "state": "IL",
                    "postalCode": "60601",
                    "country": "US",
                },
                "lineItems": [
                    {
                        "recipeSetId": "RECIPE-001",
                        "skuQuantities": [{"sku": "SKU001", "quantity": "100"}],
                    }
                ],
            }
        ]
        mock_response = Mock()
        mock_response.json.return_value = api_response
        mock_session.post.return_value = mock_response

        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            customer_id=100,
        )
        orders = list(service.read_orders())

        assert len(orders) == 1
        assert isinstance(orders[0], Order)
        assert orders[0].remote_order_id == "ORDER-001"
        mock_session.post.assert_called_once()

    def test_read_orders_posts_correct_data(self, mock_session, mock_artwork_service, mocker):
        """Test that read_orders posts the correct search parameters."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response

        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            base_url="http://api.example.com",
        )
        list(service.read_orders())

        # Verify post was called with correct endpoint and data
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        expected_url = "http://api.example.com/api/orders/search/"
        assert call_args.kwargs["url"] == expected_url

        # Verify json data includes today's date and correct workflow status
        assert "json" in call_args.kwargs
        json_data = call_args.kwargs["json"]
        assert json_data["lastModificationStartDate"] == dt.date.today().isoformat()
        assert json_data["workflowStatuses"] == ["not-started"]

    def test_read_orders_empty_response(self, mock_session, mock_artwork_service, mocker):
        """Test that read_orders handles empty API response."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_session.post.return_value = mock_response

        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
        )
        orders = list(service.read_orders())

        assert len(orders) == 0

    def test_read_orders_multiple_orders(self, mock_session, mock_artwork_service, mocker):
        """Test that read_orders yields multiple orders."""
        api_response = [
            {
                "purchaseOrderNumber": f"ORDER-{i:03d}",
                "userId": f"USER{i}",
                "emailAddress": f"user{i}@example.com",
                "phoneNumber": f"+1-555-000{i}",
                "shippingAddress": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "address1": "123 Main St",
                    "city": "Chicago",
                    "state": "IL",
                    "postalCode": "60601",
                    "country": "US",
                },
                "lineItems": [
                    {
                        "recipeSetId": f"RECIPE-{i}",
                        "skuQuantities": [{"sku": f"SKU{i}", "quantity": "100"}],
                    }
                ],
            }
            for i in range(3)
        ]
        mock_response = Mock()
        mock_response.json.return_value = api_response
        mock_session.post.return_value = mock_response

        service = SpectrumOrderService(
            session=mock_session, artwork_service=mock_artwork_service, customer_id=100
        )
        orders = list(service.read_orders())

        assert len(orders) == 3
        order_ids = {order.remote_order_id for order in orders}
        assert order_ids == {"ORDER-000", "ORDER-001", "ORDER-002"}

    def test_read_orders_handles_parsing_exception(
        self, mock_session, mock_artwork_service, mocker
    ):
        """Test that read_orders records errors and continues iteration."""
        api_response = [
            {
                "purchaseOrderNumber": "VALID-ORDER",
                "userId": "USER123",
                "emailAddress": "user@example.com",
                "phoneNumber": "+1-555-0001",
                "shippingAddress": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "address1": "123 Main St",
                    "city": "Chicago",
                    "postalCode": "60601",
                    "country": "US",
                },
                "lineItems": [
                    {
                        "recipeSetId": "RECIPE-001",
                        "skuQuantities": [{"sku": "SKU001", "quantity": "100"}],
                    }
                ],
            },
            {
                "purchaseOrderNumber": "INVALID-ORDER",
                # Missing required fields to trigger exception
            },
            {
                "purchaseOrderNumber": "ANOTHER-VALID",
                "userId": "USER456",
                "emailAddress": "user456@example.com",
                "phoneNumber": "+1-555-0002",
                "shippingAddress": {
                    "firstName": "Jane",
                    "lastName": "Smith",
                    "address1": "456 Oak Ave",
                    "city": "Boston",
                    "postalCode": "02101",
                    "country": "US",
                },
                "lineItems": [
                    {
                        "recipeSetId": "RECIPE-002",
                        "skuQuantities": [{"sku": "SKU002", "quantity": "50"}],
                    }
                ],
            },
        ]
        mock_response = Mock()
        mock_response.json.return_value = api_response
        mock_session.post.return_value = mock_response

        mock_error_store = mocker.Mock()
        mocker.patch(
            "src.services.spectrum_order_service.get_error_store", return_value=mock_error_store
        )

        service = SpectrumOrderService(
            session=mock_session, artwork_service=mock_artwork_service, customer_id=100
        )
        orders = list(service.read_orders())

        # Should have yielded 2 valid orders
        assert len(orders) == 2
        # Should have recorded the error
        assert mock_error_store.add.called


class TestMakeOrder:
    """Tests for _make_order method."""

    @pytest.fixture
    def service(self, tmp_path, mock_session, mock_artwork_service):
        """Provide a CamelbakOrderService instance."""
        return SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            administration_id=1,
            customer_id=100,
            pricelist_id=2,
            order_provider="CAMELBAK",
            shipment_type="camelbak%",
            workdays_for_delivery=3,
            input_dir=tmp_path / "input",
        )

    @pytest.fixture
    def api_order_data(self):
        """Provide sample API order data."""
        return {
            "purchaseOrderNumber": "ORDER-12345",
            "userId": "USER123",
            "emailAddress": "customer@example.com",
            "phoneNumber": "+1-555-0123",
            "shippingAddress": {
                "firstName": "John",
                "lastName": "Doe",
                "address1": "123 Main St",
                "address2": "Suite 100",
                "city": "Chicago",
                "state": "IL",
                "postalCode": "60601",
                "country": "US",
            },
            "lineItems": [
                {
                    "recipeSetId": "RECIPE-001",
                    "skuQuantities": [
                        {"sku": "SKU001", "quantity": "100"},
                        {"sku": "SKU002", "quantity": "50"},
                    ],
                }
            ],
        }

    def test_make_order_basic(self, service, api_order_data):
        """Test creating an Order from API data."""
        order = service._make_order(api_order_data)

        assert isinstance(order, Order)
        assert order.administration_id == 1
        assert order.customer_id == 100
        assert order.pricelist_id == 2
        assert order.order_provider == "CAMELBAK"
        assert order.shipment_type == "camelbak%"
        assert order.remote_order_id == "ORDER-12345"

    def test_make_order_ship_to_data(self, service, api_order_data):
        """Test that ShipTo is populated correctly from API data."""
        order = service._make_order(api_order_data)

        assert order.ship_to.remote_customer_id == "USER123"
        assert order.ship_to.company_name == ""
        assert order.ship_to.contact_name == "John Doe"
        assert order.ship_to.email == "customer@example.com"
        assert order.ship_to.phone == "+1-555-0123"
        assert order.ship_to.street1 == "123 Main St"
        assert order.ship_to.street2 == "Suite 100"
        assert order.ship_to.city == "Chicago"
        assert order.ship_to.state == "IL"
        assert order.ship_to.postal_code == "60601"
        assert order.ship_to.country_code == "US"

    def test_make_order_line_items(self, service, api_order_data):
        """Test that LineItems are created from API skuQuantities."""
        order = service._make_order(api_order_data)

        assert len(order.line_items) == 2
        assert order.line_items[0].line_id == "RECIPE-001"
        assert order.line_items[0].product_code == "SKU001"
        assert order.line_items[0].quantity == 100
        assert order.line_items[1].product_code == "SKU002"
        assert order.line_items[1].quantity == 50

    def test_make_order_multiple_recipe_sets(self, service, api_order_data):
        """Test that multiple recipe sets generate multiple line items."""
        api_order_data["lineItems"] = [
            {
                "recipeSetId": "RECIPE-001",
                "skuQuantities": [{"sku": "SKU001", "quantity": "100"}],
            },
            {
                "recipeSetId": "RECIPE-002",
                "skuQuantities": [{"sku": "SKU002", "quantity": "50"}],
            },
        ]

        order = service._make_order(api_order_data)

        assert len(order.line_items) == 2
        assert order.line_items[0].line_id == "RECIPE-001"
        assert order.line_items[1].line_id == "RECIPE-002"

    def test_make_order_no_line_items(self, service, api_order_data):
        """Test that order with empty lineItems array still validates line_items requirement."""
        api_order_data["lineItems"] = []

        # Should raise ValueError because line_items cannot be empty
        with pytest.raises(ValueError, match="Line items must be a list of LineItem instances"):
            service._make_order(api_order_data)

    def test_make_order_missing_optional_fields(self, service):
        """Test creating order with minimal data."""
        api_order_data = {
            "purchaseOrderNumber": "MINIMAL-ORDER",
            "userId": "USER999",
            "emailAddress": "minimal@example.com",
            "phoneNumber": "+1-555-9999",
            "shippingAddress": {
                "firstName": "Jane",
                "lastName": "Smith",
                "address1": "999 Unknown Ave",
                "city": "NoCity",
                "postalCode": "99999",
                "country": "XX",
            },
            "lineItems": [
                {
                    "recipeSetId": "RECIPE-MIN",
                    "skuQuantities": [{"sku": "SKU-MIN", "quantity": "1"}],
                }
            ],
        }

        order = service._make_order(api_order_data)

        assert order.remote_order_id == "MINIMAL-ORDER"
        assert order.ship_to.street2 == ""
        assert order.ship_to.state == ""
        assert len(order.line_items) == 1

    def test_make_order_description(self, service, api_order_data):
        """Test that description is formatted correctly."""
        order = service._make_order(api_order_data)

        assert "CAMELBAK order ORDER-12345" in order.description

    def test_make_order_delivery_instructions(self, service, api_order_data):
        """Test that delivery_instructions defaults to empty string."""
        order = service._make_order(api_order_data)

        assert order.delivery_instructions == ""

    def test_make_order_ship_at_is_set(self, service, api_order_data):
        """Test that ship_at is set based on workdays_for_delivery."""
        order = service._make_order(api_order_data)

        expected_ship_at = Order.calculate_delivery_date(service.workdays_for_delivery)
        # ship_at may be stored as a date or string, so compare as strings
        assert order.ship_at == expected_ship_at or str(order.ship_at) == str(expected_ship_at)

    def test_make_order_province_fallback(self, service):
        """Test that province is used if state is missing."""
        api_order_data = {
            "purchaseOrderNumber": "ORDER-CA",
            "userId": "USER-CA",
            "emailAddress": "user@ca.example.com",
            "phoneNumber": "+1-555-0001",
            "shippingAddress": {
                "firstName": "Canadian",
                "lastName": "User",
                "address1": "1 Maple Ave",
                "city": "Toronto",
                "province": "ON",
                "postalCode": "M5H 2N2",
                "country": "CA",
            },
            "lineItems": [
                {
                    "recipeSetId": "RECIPE-CA",
                    "skuQuantities": [{"sku": "SKU-CA", "quantity": "1"}],
                }
            ],
        }

        order = service._make_order(api_order_data)

        assert order.ship_to.state == "ON"


class TestShouldUpdateSale:
    """Tests for should_update_sale method."""

    def test_should_update_sale_always_returns_false(self, mock_session, mock_artwork_service):
        """Test that should_update_sale always returns False for Camelbak."""
        service = SpectrumOrderService(session=mock_session, artwork_service=mock_artwork_service)
        mock_order = Mock(spec=Order)
        mock_order.remote_order_id = "ANY-ORDER"

        result = service.should_update_sale(mock_order)

        assert result is False


class TestPersistOrder:
    """Tests for persist_order method."""

    @pytest.fixture
    def service(self, tmp_path, mock_session, mock_artwork_service):
        """Provide a CamelbakOrderService instance with temp directories."""
        input_dir = tmp_path / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        return SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            base_url="http://api.example.com",
            input_dir=input_dir,
        )

    def test_persist_order_writes_json_file(self, service, mock_session, mocker):
        """Test that persist_order writes a JSON file."""
        mock_order = mocker.Mock(spec=Order)
        mock_order.remote_order_id = "ORDER-001"
        mock_order.status = OrderStatus.CREATED
        mock_order.line_items = []

        def mock_set_status(status):
            mock_order.status = status

        mock_order.set_status = mock_set_status

        order_dict = {
            "sale_id": 0,
            "administration_id": 1,
            "customer_id": -1,
            "remote_order_id": "ORDER-001",
            "status": "CREATED",
            "ship_to": {},
            "line_items": [],
        }
        mocker.patch(
            "src.services.spectrum_order_service.asdict",
            return_value=order_dict,
        )

        mock_response = Mock()
        mock_session.put.return_value = mock_response

        service.persist_order(mock_order, OrderStatus.CREATED)

        # Verify JSON file was written
        json_file = service.input_dir / "ORDER-001.json"
        assert json_file.exists()

        # Verify JSON content
        content = json_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["remote_order_id"] == "ORDER-001"

    def test_persist_order_calls_set_status(self, service, mock_session, mocker):
        """Test that persist_order calls order.set_status."""
        mock_order = mocker.Mock(spec=Order)
        mock_order.remote_order_id = "ORDER-002"
        mock_order.status = OrderStatus.NEW
        mock_order.line_items = []

        def mock_set_status(status):
            mock_order.status = status

        mock_order.set_status = mock_set_status

        mocker.patch(
            "src.services.spectrum_order_service.asdict",
            return_value={"remote_order_id": "ORDER-002"},
        )

        mock_response = Mock()
        mock_session.put.return_value = mock_response

        service.persist_order(mock_order, OrderStatus.CONFIRMED)

        assert mock_order.status == OrderStatus.CONFIRMED

    def test_persist_order_calls_api(self, service, mock_session, mocker):
        """Test that persist_order calls the API to update order status."""
        mock_order = mocker.Mock(spec=Order)
        mock_order.remote_order_id = "ORDER-003"
        mock_order.status = OrderStatus.NEW
        mock_li1 = mocker.Mock()
        mock_li1.line_id = "RECIPE-001"
        mock_li2 = mocker.Mock()
        mock_li2.line_id = "RECIPE-002"
        mock_order.line_items = [mock_li1, mock_li2]

        def mock_set_status(status):
            mock_order.status = status

        mock_order.set_status = mock_set_status

        mocker.patch(
            "src.services.spectrum_order_service.asdict",
            return_value={"remote_order_id": "ORDER-003"},
        )

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {}
        mock_session.put.return_value = mock_response

        service.persist_order(mock_order, OrderStatus.CONFIRMED)

        # Verify API was called
        mock_session.put.assert_called_once()
        call_args = mock_session.put.call_args
        expected_url = "http://api.example.com/api/order/status/"
        assert call_args.kwargs["url"] == expected_url

        # Verify json data structure
        json_data = call_args.kwargs["json"]
        assert json_data["purchaseOrderNumber"] == "ORDER-003"
        assert len(json_data["lineItems"]) == 2
        assert all(li["workflowStatus"] == "in-progress" for li in json_data["lineItems"])

    def test_persist_order_datetime_serialization(self, service, mock_session, mocker):
        """Test that datetime objects are properly serialized."""
        mock_order = mocker.Mock(spec=Order)
        mock_order.remote_order_id = "ORDER-004"
        mock_order.status = OrderStatus.NEW
        mock_order.line_items = []

        def mock_set_status(status):
            mock_order.status = status

        mock_order.set_status = mock_set_status

        created_at = dt.datetime(2025, 3, 15, 10, 30, 45, tzinfo=dt.UTC)
        order_dict = {
            "remote_order_id": "ORDER-004",
            "created_at": created_at,
            "ship_at": dt.date(2025, 3, 18),
        }
        mocker.patch(
            "src.services.spectrum_order_service.asdict",
            return_value=order_dict,
        )

        mock_response = Mock()
        mock_session.put.return_value = mock_response

        service.persist_order(mock_order, OrderStatus.CONFIRMED)

        # Verify JSON file contains ISO format dates
        json_file = service.input_dir / "ORDER-004.json"
        content = json_file.read_text(encoding="utf-8")
        assert "2025-03-15" in content
        assert "2025-03-18" in content


class TestLoadOrder:
    """Tests for load_order method."""

    @pytest.fixture
    def service(self, tmp_path, mock_session, mock_artwork_service):
        """Provide a CamelbakOrderService instance with temp directories."""
        input_dir = tmp_path / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        return SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            input_dir=input_dir,
        )

    def test_load_order_reads_json_file(self, service):
        """Test that load_order reads and parses a JSON file."""
        order_json = {
            "sale_id": 1,
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "CAMELBAK",
            "pricelist_id": 2,
            "remote_order_id": "LOADED-001",
            "shipment_type": "camelbak%",
            "description": "Test order",
            "delivery_instructions": "",
            "ship_to": {
                "remote_customer_id": "USER123",
                "company_name": "",
                "contact_name": "John Doe",
                "email": "john@example.com",
                "phone": "+1-555-0123",
                "street1": "123 Main St",
                "street2": "",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country_code": "US",
            },
            "line_items": [
                {
                    "line_id": "RECIPE-001",
                    "product_code": "SKU001",
                    "quantity": 100,
                    "artwork": None,
                }
            ],
            "status": "created",
            "created_at": "2025-03-15T10:30:45+00:00",
            "ship_at": "2025-03-18",
        }

        # Write JSON file
        json_file = service.input_dir / "LOADED-001.json"
        json_file.write_text(json.dumps(order_json), encoding="utf-8")

        # Load and verify
        order = service.load_order("LOADED-001")

        assert isinstance(order, Order)
        assert order.remote_order_id == "LOADED-001"
        assert order.ship_to.contact_name == "John Doe"
        assert len(order.line_items) == 1
        assert order.status == OrderStatus.CREATED

    def test_load_order_preserves_datetime_fields(self, service):
        """Test that load_order properly parses datetime fields."""
        order_json = {
            "sale_id": 1,
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "CAMELBAK",
            "pricelist_id": 2,
            "remote_order_id": "DATETIME-001",
            "shipment_type": "camelbak%",
            "description": "Test",
            "delivery_instructions": "",
            "ship_to": {
                "remote_customer_id": "USER",
                "company_name": "",
                "contact_name": "Test",
                "email": "test@example.com",
                "phone": "+1-555-0000",
                "street1": "123 St",
                "street2": "",
                "city": "City",
                "state": "ST",
                "postal_code": "12345",
                "country_code": "US",
            },
            "line_items": [
                {
                    "line_id": "RECIPE-DT",
                    "product_code": "SKU-DT",
                    "quantity": 1,
                    "artwork": None,
                }
            ],
            "status": "new",
            "created_at": "2025-02-14T15:45:30+00:00",
            "ship_at": "2025-02-21",
        }

        json_file = service.input_dir / "DATETIME-001.json"
        json_file.write_text(json.dumps(order_json), encoding="utf-8")

        order = service.load_order("DATETIME-001")

        # created_at should contain the correct date
        assert "2025-02-14" in str(order.created_at)
        # ship_at is always set to today's date by load_order
        assert str(order.ship_at) == str(dt.date.today())

    def test_load_order_handles_artwork(self, service):
        """Test that load_order properly reconstructs Artwork objects."""
        # Create temporary files for design_paths
        design_file1 = service.input_dir / "design1.png"
        design_file1.write_text("fake design")
        design_file2 = service.input_dir / "design2.png"
        design_file2.write_text("fake design")
        placement_file = service.input_dir / "placement.png"
        placement_file.write_text("fake placement")

        order_json = {
            "sale_id": 1,
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "CAMELBAK",
            "pricelist_id": 2,
            "remote_order_id": "ARTWORK-001",
            "shipment_type": "camelbak%",
            "description": "Test",
            "delivery_instructions": "",
            "ship_to": {
                "remote_customer_id": "USER",
                "company_name": "",
                "contact_name": "Test",
                "email": "test@example.com",
                "phone": "+1-555-0000",
                "street1": "123 St",
                "street2": "",
                "city": "City",
                "state": "ST",
                "postal_code": "12345",
                "country_code": "US",
            },
            "line_items": [
                {
                    "line_id": "RECIPE-001",
                    "product_code": "SKU001",
                    "quantity": 100,
                    "artwork": {
                        "artwork_id": "ART-001",
                        "artwork_line_id": "ART-LI-001",
                        "design_url": "http://example.com/design.png",
                        "design_paths": [str(design_file1), str(design_file2)],
                        "placement_url": "http://example.com/placement.png",
                        "placement_path": str(placement_file),
                    },
                }
            ],
            "status": "new",
            "created_at": "2025-03-15T10:30:45+00:00",
            "ship_at": "2025-03-18",
        }

        json_file = service.input_dir / "ARTWORK-001.json"
        json_file.write_text(json.dumps(order_json), encoding="utf-8")

        order = service.load_order("ARTWORK-001")

        assert order.line_items[0].artwork is not None
        assert order.line_items[0].artwork.artwork_id == "ART-001"
        assert len(order.line_items[0].artwork.design_paths) == 2


class TestNotifyCompletedSale:
    """Tests for notify_completed_sale method."""

    def test_notify_completed_sale_calls_api(self, mock_session, mock_artwork_service, mocker):
        """Test that notify_completed_sale calls the API with correct data."""
        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            base_url="http://api.example.com",
        )

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {}
        mock_session.post.return_value = mock_response

        mock_order = mocker.Mock(spec=Order)
        mock_order.remote_order_id = "ORDER-001"
        mock_li1 = mocker.Mock()
        mock_li1.line_id = "RECIPE-001"
        mock_li2 = mocker.Mock()
        mock_li2.line_id = "RECIPE-002"
        mock_order.line_items = [mock_li1, mock_li2]

        notify_data = {"carrier_tracking_ref": "TRACK-123456"}

        service.notify_completed_sale(mock_order, notify_data)

        # Verify API was called
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        expected_url = "http://api.example.com/api/order/ship-notification/"
        assert call_args.kwargs["url"] == expected_url

        # Verify json data structure
        json_data = call_args.kwargs["json"]
        assert json_data["purchaseOrderNumber"] == "ORDER-001"
        assert len(json_data["lineItems"]) == 2
        assert json_data["lineItems"][0]["recipeSetReadableId"] == "RECIPE-001"
        assert json_data["lineItems"][0]["shipmentTracking"] == "TRACK-123456"

    def test_notify_completed_sale_empty_tracking(self, mock_session, mock_artwork_service, mocker):
        """Test notify_completed_sale with empty tracking reference."""
        service = SpectrumOrderService(
            session=mock_session,
            artwork_service=mock_artwork_service,
            base_url="http://api.example.com",
        )

        mock_order = mocker.Mock(spec=Order)
        mock_order.remote_order_id = "ORDER-002"
        mock_li = mocker.Mock()
        mock_li.line_id = "RECIPE-001"
        mock_order.line_items = [mock_li]

        notify_data = {"carrier_tracking_ref": ""}
        mock_response = Mock()
        mock_session.post.return_value = mock_response

        service.notify_completed_sale(mock_order, notify_data)

        call_args = mock_session.post.call_args
        json_data = call_args[1]["json"]
        assert json_data["lineItems"][0]["shipmentTracking"] == ""


class TestGetNotifyData:
    """Tests for get_notify_data method."""

    def test_get_notify_data_retrieves_shipping_info(
        self, mock_session, mock_artwork_service, mocker
    ):
        """Test that get_notify_data retrieves shipping info from sale service."""
        service = SpectrumOrderService(session=mock_session, artwork_service=mock_artwork_service)

        mock_order = mocker.Mock(spec=Order)
        mock_order.remote_order_id = "ORDER-001"

        mock_sale_service = mocker.Mock()
        shipping_info = [{"carrier_tracking_ref": "TRACK-123456, TRACK-789012"}]
        mock_sale_service.search_shipping_info.return_value = shipping_info

        result = service.get_notify_data(mock_order, mock_sale_service)

        assert isinstance(result, dict)
        assert "carrier_tracking_ref" in result
        mock_sale_service.search_shipping_info.assert_called_once_with(mock_order)

    def test_get_notify_data_splits_tracking_refs(self, mock_session, mock_artwork_service, mocker):
        """Test that get_notify_data properly splits tracking references."""
        service = SpectrumOrderService(session=mock_session, artwork_service=mock_artwork_service)

        mock_order = mocker.Mock(spec=Order)
        mock_sale_service = mocker.Mock()
        shipping_info = [{"carrier_tracking_ref": "TRACK-001, TRACK-002, TRACK-003"}]
        mock_sale_service.search_shipping_info.return_value = shipping_info

        result = service.get_notify_data(mock_order, mock_sale_service)

        assert result["carrier_tracking_ref"] == ["TRACK-001", "TRACK-002", "TRACK-003"]
