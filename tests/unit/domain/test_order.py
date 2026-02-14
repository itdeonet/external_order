"""Unit tests for the Order domain class."""

import datetime as dt

import pytest

from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.line_item import LineItem
from src.domain.order import Order, OrderStatus
from src.domain.ship_to import ShipTo


class TestOrderStatus:
    """Tests for OrderStatus enum."""

    def test_order_status_values(self):
        """Test that OrderStatus enum has expected values."""
        assert OrderStatus.NEW.value == "new"
        assert OrderStatus.CREATED.value == "created"
        assert OrderStatus.ARTWORK.value == "artwork"
        assert OrderStatus.COMPLETED.value == "completed"
        assert OrderStatus.SHIPPED.value == "shipped"
        assert OrderStatus.FAILED.value == "failed"

    def test_order_status_enum_members(self):
        """Test that all expected OrderStatus members exist."""
        statuses = {member.name for member in OrderStatus}
        expected = {"NEW", "CREATED", "ARTWORK", "COMPLETED", "SHIPPED", "FAILED"}
        assert statuses == expected


class TestOrderInstantiation:
    """Tests for basic Order instantiation."""

    @pytest.fixture
    def valid_ship_to(self):
        """Provide a valid ShipTo instance."""
        return ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )

    @pytest.fixture
    def valid_line_item(self, mocker):
        """Provide a mocked LineItem instance."""
        line_item = mocker.Mock(spec=LineItem)
        return line_item

    @pytest.fixture
    def valid_order_data(self, valid_ship_to, valid_line_item):
        """Provide valid Order initialization data."""
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Harman",
            "pricelist_id": 50,
            "remote_order_id": "ORD-12345",
            "shipment_type": "standard",
            "ship_to": valid_ship_to,
            "line_items": [valid_line_item],
        }

    def test_instantiation_with_all_fields(self, valid_order_data):
        """Test creating an Order with all fields."""
        order = Order(**valid_order_data)

        assert order.administration_id == 1
        assert order.customer_id == 100
        assert order.order_provider == "Harman"
        assert order.pricelist_id == 50
        assert order.remote_order_id == "ORD-12345"
        assert order.shipment_type == "standard"
        assert order.ship_to is valid_order_data["ship_to"]
        assert order.line_items == valid_order_data["line_items"]

    def test_instantiation_defaults(self, valid_order_data):
        """Test that Order has correct default values."""
        order = Order(**valid_order_data)

        assert order.id == 0
        assert order.status == OrderStatus.NEW
        assert order.artwork_service is None
        assert isinstance(order.created_at, dt.datetime)

    def test_id_not_settable_via_init(self, valid_order_data):
        """Test that id cannot be set via __init__."""
        with pytest.raises(TypeError):
            Order(id=999, **valid_order_data)  # type: ignore

    def test_status_not_settable_via_init(self, valid_order_data):
        """Test that status cannot be set via __init__."""
        with pytest.raises(TypeError):
            Order(status=OrderStatus.CREATED, **valid_order_data)  # type: ignore

    def test_created_at_not_settable_via_init(self, valid_order_data):
        """Test that created_at cannot be set via __init__."""
        with pytest.raises(TypeError):
            Order(created_at=dt.datetime.now(dt.UTC), **valid_order_data)  # type: ignore


class TestOrderAdministrationIDValidation:
    """Tests for administration_id field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_administration_id_required(self, minimal_order_data):
        """Test that administration_id is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_administration_id_zero_raises_error(self, minimal_order_data):
        """Test that administration_id of 0 raises ValueError."""
        with pytest.raises(ValueError, match="Administration ID must be a positive integer"):
            Order(administration_id=0, **minimal_order_data)

    def test_administration_id_negative_raises_error(self, minimal_order_data):
        """Test that negative administration_id raises ValueError."""
        with pytest.raises(ValueError, match="Administration ID must be a positive integer"):
            Order(administration_id=-1, **minimal_order_data)

    def test_administration_id_not_int_raises_error(self, minimal_order_data):
        """Test that non-integer administration_id raises ValueError."""
        with pytest.raises(ValueError, match="Administration ID must be a positive integer"):
            Order(administration_id="123", **minimal_order_data)  # type: ignore

    def test_administration_id_valid(self, minimal_order_data):
        """Test that valid administration_id is accepted."""
        order = Order(administration_id=1, **minimal_order_data)
        assert order.administration_id == 1


class TestOrderCustomerIDValidation:
    """Tests for customer_id field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_customer_id_required(self, minimal_order_data):
        """Test that customer_id is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_customer_id_zero_raises_error(self, minimal_order_data):
        """Test that customer_id of 0 raises ValueError."""
        with pytest.raises(ValueError, match="Customer ID must be a positive integer"):
            Order(customer_id=0, **minimal_order_data)

    def test_customer_id_negative_raises_error(self, minimal_order_data):
        """Test that negative customer_id raises ValueError."""
        with pytest.raises(ValueError, match="Customer ID must be a positive integer"):
            Order(customer_id=-1, **minimal_order_data)

    def test_customer_id_not_int_raises_error(self, minimal_order_data):
        """Test that non-integer customer_id raises ValueError."""
        with pytest.raises(ValueError, match="Customer ID must be a positive integer"):
            Order(customer_id="100", **minimal_order_data)  # type: ignore

    def test_customer_id_valid(self, minimal_order_data):
        """Test that valid customer_id is accepted."""
        order = Order(customer_id=100, **minimal_order_data)
        assert order.customer_id == 100


class TestOrderOrderProviderValidation:
    """Tests for order_provider field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_order_provider_required(self, minimal_order_data):
        """Test that order_provider is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_order_provider_empty_raises_error(self, minimal_order_data):
        """Test that empty order_provider raises ValueError."""
        with pytest.raises(ValueError, match="Order provider must be a non-empty string"):
            Order(order_provider="", **minimal_order_data)

    def test_order_provider_whitespace_only_raises_error(self, minimal_order_data):
        """Test that whitespace-only order_provider raises ValueError."""
        with pytest.raises(ValueError, match="Order provider must be a non-empty string"):
            Order(order_provider="   ", **minimal_order_data)

    def test_order_provider_not_string_raises_error(self, minimal_order_data):
        """Test that non-string order_provider raises ValueError."""
        with pytest.raises(ValueError, match="Order provider must be a non-empty string"):
            Order(order_provider=123, **minimal_order_data)  # type: ignore

    def test_order_provider_gets_stripped(self, minimal_order_data):
        """Test that whitespace around order_provider is stripped."""
        order = Order(order_provider="  Harman  ", **minimal_order_data)
        assert order.order_provider == "Harman"


class TestOrderPricelistIDValidation:
    """Tests for pricelist_id field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_pricelist_id_required(self, minimal_order_data):
        """Test that pricelist_id is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_pricelist_id_zero_raises_error(self, minimal_order_data):
        """Test that pricelist_id of 0 raises ValueError."""
        with pytest.raises(ValueError, match="Pricelist ID must be a positive integer"):
            Order(pricelist_id=0, **minimal_order_data)

    def test_pricelist_id_negative_raises_error(self, minimal_order_data):
        """Test that negative pricelist_id raises ValueError."""
        with pytest.raises(ValueError, match="Pricelist ID must be a positive integer"):
            Order(pricelist_id=-1, **minimal_order_data)

    def test_pricelist_id_valid(self, minimal_order_data):
        """Test that valid pricelist_id is accepted."""
        order = Order(pricelist_id=50, **minimal_order_data)
        assert order.pricelist_id == 50


class TestOrderRemoteOrderIDValidation:
    """Tests for remote_order_id field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "shipment_type": "standard",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_remote_order_id_required(self, minimal_order_data):
        """Test that remote_order_id is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_remote_order_id_empty_raises_error(self, minimal_order_data):
        """Test that empty remote_order_id raises ValueError."""
        with pytest.raises(ValueError, match="Remote order ID must be a non-empty string"):
            Order(remote_order_id="", **minimal_order_data)

    def test_remote_order_id_whitespace_only_raises_error(self, minimal_order_data):
        """Test that whitespace-only remote_order_id raises ValueError."""
        with pytest.raises(ValueError, match="Remote order ID must be a non-empty string"):
            Order(remote_order_id="   ", **minimal_order_data)

    def test_remote_order_id_not_string_raises_error(self, minimal_order_data):
        """Test that non-string remote_order_id raises ValueError."""
        with pytest.raises(ValueError, match="Remote order ID must be a non-empty string"):
            Order(remote_order_id=12345, **minimal_order_data)  # type: ignore

    def test_remote_order_id_gets_stripped(self, minimal_order_data):
        """Test that whitespace around remote_order_id is stripped."""
        order = Order(remote_order_id="  ORD-123  ", **minimal_order_data)
        assert order.remote_order_id == "ORD-123"


class TestOrderShipmentTypeValidation:
    """Tests for shipment_type field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_shipment_type_required(self, minimal_order_data):
        """Test that shipment_type is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_shipment_type_empty_raises_error(self, minimal_order_data):
        """Test that empty shipment_type raises ValueError."""
        with pytest.raises(ValueError, match="Shipment type must be a non-empty string"):
            Order(shipment_type="", **minimal_order_data)

    def test_shipment_type_whitespace_only_raises_error(self, minimal_order_data):
        """Test that whitespace-only shipment_type raises ValueError."""
        with pytest.raises(ValueError, match="Shipment type must be a non-empty string"):
            Order(shipment_type="   ", **minimal_order_data)

    def test_shipment_type_not_string_raises_error(self, minimal_order_data):
        """Test that non-string shipment_type raises ValueError."""
        with pytest.raises(ValueError, match="Shipment type must be a non-empty string"):
            Order(shipment_type=123, **minimal_order_data)  # type: ignore

    def test_shipment_type_gets_stripped(self, minimal_order_data):
        """Test that whitespace around shipment_type is stripped."""
        order = Order(shipment_type="  express  ", **minimal_order_data)
        assert order.shipment_type == "express"


class TestOrderShipToValidation:
    """Tests for ship_to field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "line_items": [line_item],
        }

    def test_ship_to_required(self, minimal_order_data):
        """Test that ship_to is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_ship_to_must_be_ship_to_instance(self, minimal_order_data):
        """Test that ship_to must be a ShipTo instance."""
        with pytest.raises(ValueError, match="Ship to must be an instance of ShipTo"):
            Order(ship_to="not a ShipTo", **minimal_order_data)  # type: ignore

    def test_ship_to_none_raises_error(self, minimal_order_data):
        """Test that None ship_to raises ValueError."""
        with pytest.raises(ValueError, match="Ship to must be an instance of ShipTo"):
            Order(ship_to=None, **minimal_order_data)  # type: ignore

    def test_ship_to_valid(self, minimal_order_data, mocker):
        """Test that valid ship_to is accepted."""
        ship_to = mocker.Mock(spec=ShipTo)
        order = Order(ship_to=ship_to, **minimal_order_data)
        assert order.ship_to is ship_to


class TestOrderLineItemsValidation:
    """Tests for line_items field validation."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": ship_to,
        }

    def test_line_items_required(self, minimal_order_data):
        """Test that line_items is required."""
        with pytest.raises(ValueError):
            Order(**minimal_order_data)

    def test_line_items_empty_list_raises_error(self, minimal_order_data):
        """Test that empty line_items list raises ValueError."""
        with pytest.raises(ValueError, match="Line items must be a list of LineItem instances"):
            Order(line_items=[], **minimal_order_data)

    def test_line_items_not_list_raises_error(self, minimal_order_data):
        """Test that non-list line_items raises ValueError."""
        with pytest.raises(ValueError, match="Line items must be a list of LineItem instances"):
            Order(line_items="not a list", **minimal_order_data)  # type: ignore

    def test_line_items_none_raises_error(self, minimal_order_data):
        """Test that None line_items raises ValueError."""
        with pytest.raises(ValueError, match="Line items must be a list of LineItem instances"):
            Order(line_items=None, **minimal_order_data)  # type: ignore

    def test_line_items_contains_non_line_item_raises_error(self, minimal_order_data, mocker):
        """Test that line_items containing non-LineItem objects raises ValueError."""
        with pytest.raises(ValueError, match="Line items must be a list of LineItem instances"):
            Order(line_items=["not a LineItem"], **minimal_order_data)  # type: ignore

    def test_line_items_valid(self, minimal_order_data, mocker):
        """Test that valid line_items are accepted."""
        line_item = mocker.Mock(spec=LineItem)
        order = Order(line_items=[line_item], **minimal_order_data)
        assert order.line_items == [line_item]

    def test_line_items_multiple_valid(self, minimal_order_data, mocker):
        """Test that multiple valid line_items are accepted."""
        line_item1 = mocker.Mock(spec=LineItem)
        line_item2 = mocker.Mock(spec=LineItem)
        order = Order(line_items=[line_item1, line_item2], **minimal_order_data)
        assert order.line_items == [line_item1, line_item2]


class TestOrderArtworkServiceHandling:
    """Tests for artwork_service field handling."""

    @pytest.fixture
    def minimal_order_data(self, mocker):
        """Provide minimal valid Order data."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_artwork_service_defaults_to_none(self, minimal_order_data):
        """Test that artwork_service defaults to None."""
        order = Order(**minimal_order_data)
        assert order.artwork_service is None

    def test_artwork_service_invalid_type_becomes_none(self, minimal_order_data):
        """Test that invalid artwork_service type defaults to None."""
        order = Order(artwork_service="not a service", **minimal_order_data)  # type: ignore
        assert order.artwork_service is None

    def test_artwork_service_valid(self, minimal_order_data, mocker):
        """Test that valid artwork_service is accepted."""
        artwork_service = mocker.Mock(spec=IArtworkService)
        order = Order(artwork_service=artwork_service, **minimal_order_data)
        assert order.artwork_service is artwork_service


class TestOrderSetID:
    """Tests for set_id method."""

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_set_id_valid(self, order):
        """Test setting a valid ID."""
        order.set_id(999)
        assert order.id == 999

    def test_set_id_zero_raises_error(self, order):
        """Test that setting ID to 0 raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a positive integer"):
            order.set_id(0)

    def test_set_id_negative_raises_error(self, order):
        """Test that setting negative ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a positive integer"):
            order.set_id(-1)

    def test_set_id_non_int_raises_error(self, order):
        """Test that setting non-integer ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a positive integer"):
            order.set_id("123")


class TestOrderSetStatus:
    """Tests for set_status method."""

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_set_status_valid(self, order):
        """Test setting a valid status."""
        order.set_status(OrderStatus.CREATED)
        assert order.status == OrderStatus.CREATED

    def test_set_status_all_statuses(self, order):
        """Test setting all available statuses."""
        for status in OrderStatus:
            order.set_status(status)
            assert order.status == status

    def test_set_status_non_status_raises_error(self, order):
        """Test that setting non-OrderStatus value raises ValueError."""
        with pytest.raises(ValueError, match="Status must be an instance of OrderStatus"):
            order.set_status("invalid")

    def test_set_status_none_raises_error(self, order):
        """Test that setting status to None raises ValueError."""
        with pytest.raises(ValueError, match="Status must be an instance of OrderStatus"):
            order.set_status(None)


class TestOrderSetArtworkService:
    """Tests for set_artwork_service method."""

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_set_artwork_service_valid(self, order, mocker):
        """Test setting a valid artwork service."""
        artwork_service = mocker.Mock(spec=IArtworkService)
        order.set_artwork_service(artwork_service)
        assert order.artwork_service is artwork_service

    def test_set_artwork_service_non_service_raises_error(self, order):
        """Test that setting non-ArtworkService value raises ValueError."""
        with pytest.raises(
            ValueError, match="Artwork service must be an instance of ArtworkService"
        ):
            order.set_artwork_service("not a service")

    def test_set_artwork_service_none_raises_error(self, order):
        """Test that setting artwork service to None raises ValueError."""
        with pytest.raises(
            ValueError, match="Artwork service must be an instance of ArtworkService"
        ):
            order.set_artwork_service(None)


class TestOrderGetDeliveryDate:
    """Tests for get_delivery_date method."""

    @pytest.fixture
    def order_with_set_date(self, mocker):
        """Provide an Order instance with a controlled created_at date."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        # Set a known created_at date: Monday, Feb 10, 2025
        known_date = dt.datetime(2025, 2, 10, 10, 0, 0, tzinfo=dt.UTC)
        object.__setattr__(order, "created_at", known_date)
        return order

    def test_get_delivery_date_zero_workdays(self, order_with_set_date):
        """Test delivery date with 0 workdays."""
        delivery_date = order_with_set_date.get_delivery_date(0)
        assert delivery_date == dt.date(2025, 2, 10)

    def test_get_delivery_date_one_workday(self, order_with_set_date):
        """Test delivery date with 1 workday (Monday to Tuesday)."""
        delivery_date = order_with_set_date.get_delivery_date(1)
        assert delivery_date == dt.date(2025, 2, 11)

    def test_get_delivery_date_skips_weekends(self, order_with_set_date):
        """Test that delivery date calculation skips weekends."""
        # From Monday Feb 10, 5 workdays should be Monday Feb 17
        delivery_date = order_with_set_date.get_delivery_date(5)
        assert delivery_date == dt.date(2025, 2, 17)
        assert delivery_date.weekday() == 0  # Monday

    def test_get_delivery_date_multiple_weeks(self, order_with_set_date):
        """Test delivery date calculation across multiple weeks."""
        # 10 workdays from Monday Feb 10 should skip 2 weekends
        delivery_date = order_with_set_date.get_delivery_date(10)
        # Should land on Monday Feb 24
        assert delivery_date == dt.date(2025, 2, 24)
        assert delivery_date.weekday() == 0  # Monday

    def test_get_delivery_date_from_friday(self, mocker):
        """Test delivery date calculation starting from Friday."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        # Friday, Feb 14, 2025
        known_date = dt.datetime(2025, 2, 14, 10, 0, 0, tzinfo=dt.UTC)
        object.__setattr__(order, "created_at", known_date)

        # 1 workday from Friday should be Monday
        delivery_date = order.get_delivery_date(1)
        assert delivery_date == dt.date(2025, 2, 17)
        assert delivery_date.weekday() == 0  # Monday


class TestOrderDescription:
    """Tests for description property."""

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="ORD-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_description_format(self, order):
        """Test that description has correct format."""
        assert order.description == "Harman Order ORD-12345"

    def test_description_different_providers(self, mocker):
        """Test description with different order providers."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)

        providers = ["Harman", "Odoo", "Spectrum"]
        for provider in providers:
            order = Order(
                administration_id=1,
                customer_id=100,
                order_provider=provider,
                pricelist_id=50,
                remote_order_id="ORD-99999",
                shipment_type="standard",
                ship_to=ship_to,
                line_items=[line_item],
            )
            assert order.description == f"{provider} Order ORD-99999"


class TestOrderImmutability:
    """Tests for Order immutability (frozen dataclass)."""

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_cannot_modify_administration_id(self, order):
        """Test that administration_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            order.administration_id = 2

    def test_cannot_modify_customer_id(self, order):
        """Test that customer_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            order.customer_id = 200

    def test_cannot_modify_order_provider(self, order):
        """Test that order_provider cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            order.order_provider = "NewProvider"

    def test_cannot_modify_remote_order_id(self, order):
        """Test that remote_order_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            order.remote_order_id = "ORD-999"

    def test_cannot_modify_shipment_type(self, order):
        """Test that shipment_type cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            order.shipment_type = "express"

    def test_cannot_modify_line_items(self, order):
        """Test that line_items cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            order.line_items = []

    def test_can_modify_via_setter_methods(self, order, mocker):
        """Test that settable fields can be modified via setter methods."""
        artwork_service = mocker.Mock(spec=IArtworkService)
        order.set_artwork_service(artwork_service)
        assert order.artwork_service is artwork_service

        order.set_id(999)
        assert order.id == 999

        order.set_status(OrderStatus.SHIPPED)
        assert order.status == OrderStatus.SHIPPED


class TestOrderEquality:
    """Tests for Order equality comparison."""

    @pytest.fixture
    def order_data(self, mocker):
        """Provide Order data for equality tests."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_not_equal_orders_with_same_data(self, order_data, mocker):
        """Test that orders with same data are not equal."""
        # Use same mocked objects
        ship_to = order_data["ship_to"]
        line_items = order_data["line_items"]

        order1 = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=line_items,
        )
        order2 = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=line_items,
        )

        assert order1 != order2

    def test_different_customer_ids_not_equal(self, order_data):
        """Test that orders with different customer IDs are not equal."""
        order1 = Order(
            customer_id=100, **{k: v for k, v in order_data.items() if k != "customer_id"}
        )
        order2 = Order(
            customer_id=200, **{k: v for k, v in order_data.items() if k != "customer_id"}
        )

        assert order1 != order2
