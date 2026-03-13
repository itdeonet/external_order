"""Unit tests for the Order domain class."""

import datetime as dt

import pytest

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
        assert OrderStatus.CONFIRMED.value == "confirmed"
        assert OrderStatus.COMPLETED.value == "completed"
        assert OrderStatus.SHIPPED.value == "shipped"
        assert OrderStatus.FAILED.value == "failed"

    def test_order_status_enum_members(self):
        """Test that all expected OrderStatus members exist."""
        statuses = {member.name for member in OrderStatus}
        expected = {"NEW", "CREATED", "ARTWORK", "CONFIRMED", "COMPLETED", "SHIPPED", "FAILED"}
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
    def valid_line_item(self):
        """Provide a LineItem instance."""
        return LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)

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
            "description": "Harman Order ORD-12345",
            "delivery_instructions": "Please deliver on weekday between 8-17",
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

        assert order.sale_id == 0
        assert order.status == OrderStatus.NEW
        assert isinstance(order.created_at, str)
        assert isinstance(order.ship_at, str)

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

    def test_ship_at_not_settable_via_init(self, valid_order_data):
        """Test that ship_at cannot be set via __init__."""
        with pytest.raises(TypeError):
            Order(ship_at=dt.date.today(), **valid_order_data)  # type: ignore


class TestOrderAdministrationIDValidation:
    """Tests for administration_id field validation."""

    @pytest.fixture
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "delivery_instructions": "Please deliver on weekday between 8-17",
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
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
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
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
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
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
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
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "shipment_type": "standard",
            "description": "Test order",
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
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "description": "Test order",
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
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
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

    def test_ship_to_valid(self, minimal_order_data):
        """Test that valid ship_to is accepted."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        order = Order(ship_to=ship_to, **minimal_order_data)
        assert order.ship_to is ship_to


class TestOrderLineItemsValidation:
    """Tests for line_items field validation."""

    @pytest.fixture
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
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

    def test_line_items_contains_non_line_item_raises_error(self, minimal_order_data):
        """Test that line_items containing non-LineItem objects raises ValueError."""
        with pytest.raises(ValueError, match="Line items must be a list of LineItem instances"):
            Order(line_items=["not a LineItem"], **minimal_order_data)  # type: ignore

    def test_line_items_valid(self, minimal_order_data):
        """Test that valid line_items are accepted."""
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        order = Order(line_items=[line_item], **minimal_order_data)
        assert order.line_items == [line_item]

    def test_line_items_multiple_valid(self, minimal_order_data):
        """Test that multiple valid line_items are accepted."""
        line_item1 = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        line_item2 = LineItem(line_id="RL-002", product_code="PROD-002", quantity=10)

        order = Order(line_items=[line_item1, line_item2], **minimal_order_data)
        assert order.line_items == [line_item1, line_item2]


class TestOrderSetSaleID:
    """Tests for set_sale_id method."""

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_set_sale_id_valid(self, order):
        """Test setting a valid ID."""
        order.set_sale_id(999)
        assert order.sale_id == 999

    def test_set_sale_id_zero_raises_error(self, order):
        """Test that setting ID to 0 raises ValueError."""
        with pytest.raises(ValueError, match="value must be a positive integer"):
            order.set_sale_id(0)

    def test_set_sale_id_negative_raises_error(self, order):
        """Test that setting negative ID raises ValueError."""
        with pytest.raises(ValueError, match="value must be a positive integer"):
            order.set_sale_id(-1)

    def test_set_sale_id_non_int_raises_error(self, order):
        """Test that setting non-integer ID raises ValueError."""
        with pytest.raises(ValueError, match="value must be a positive integer"):
            order.set_sale_id("123")


class TestOrderSetStatus:
    """Tests for set_status method."""

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
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


class TestOrderCalculateDeliveryDate:
    """Tests for calculate_delivery_date static method."""

    def test_calculate_delivery_date_zero_workdays(self):
        """Test delivery date with 0 workdays."""
        today = dt.date.today()
        delivery_date = Order.calculate_delivery_date(0)
        assert delivery_date == today

    def test_calculate_delivery_date_one_workday(self):
        """Test delivery date with 1 workday."""
        today = dt.date.today()
        delivery_date = Order.calculate_delivery_date(1)

        # Calculate expected date (skip weekends if needed)
        expected = today + dt.timedelta(days=1)
        while expected.weekday() >= 5:  # Skip weekends
            expected += dt.timedelta(days=1)

        assert delivery_date == expected

    def test_calculate_delivery_date_spans_weekend(self):
        """Test that delivery date calculation skips weekends."""
        # We calculate 5 workdays from today
        delivery_date = Order.calculate_delivery_date(5)

        # Should be a workday (Monday-Friday)
        assert delivery_date.weekday() < 5

    def test_calculate_delivery_date_multiple_weeks(self):
        """Test delivery date calculation across multiple weeks."""
        # 10 workdays should span at least one weekend
        delivery_date = Order.calculate_delivery_date(10)

        # Should be a workday (Monday-Friday)
        assert delivery_date.weekday() < 5

        # Should be at least 10 days in the future (accounting for weekends)
        today = dt.date.today()
        assert (delivery_date - today).days >= 10

    def test_calculate_delivery_date_negative_workdays_raises_error(self):
        """Test that negative workdays raises ValueError."""
        with pytest.raises(
            ValueError, match="Workdays for delivery must be a non-negative integer"
        ):
            Order.calculate_delivery_date(-1)

    def test_calculate_delivery_date_can_be_called_from_instance(self):
        """Test that static method can also be called from an instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

        today = dt.date.today()
        delivery_date = order.calculate_delivery_date(0)
        assert delivery_date == today


class TestOrderSetCreatedAt:
    """Tests for set_created_at method."""

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_set_created_at_valid(self, order):
        """Test setting a valid created_at datetime."""
        now_utc = dt.datetime.now(dt.UTC)
        order.set_created_at(now_utc)
        assert order.created_at == now_utc.isoformat()

    def test_set_created_at_past_datetime(self, order):
        """Test setting a past datetime."""
        past_datetime = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt.UTC)
        order.set_created_at(past_datetime)
        assert order.created_at == past_datetime.isoformat()

    def test_set_created_at_naive_datetime(self, order):
        """Test setting a naive datetime (without timezone)."""
        naive_datetime = dt.datetime(2025, 2, 14, 10, 30, 45)
        order.set_created_at(naive_datetime)
        assert order.created_at == naive_datetime.isoformat()

    def test_set_created_at_non_datetime_raises_error(self, order):
        """Test that setting non-datetime value raises ValueError."""
        with pytest.raises(ValueError, match="Created at must be a datetime instance"):
            order.set_created_at("2025-02-14T10:30:45")  # type: ignore

    def test_set_created_at_date_raises_error(self, order):
        """Test that setting date instead of datetime raises ValueError."""
        with pytest.raises(ValueError, match="Created at must be a datetime instance"):
            order.set_created_at(dt.date.today())  # type: ignore

    def test_set_created_at_none_raises_error(self, order):
        """Test that setting created_at to None raises ValueError."""
        with pytest.raises(ValueError, match="Created at must be a datetime instance"):
            order.set_created_at(None)  # type: ignore


class TestOrderSetShipAt:
    """Tests for set_ship_at method."""

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_set_ship_at_valid(self, order):
        """Test setting a valid ship_at date."""
        future_date = dt.date.today() + dt.timedelta(days=5)
        order.set_ship_at(future_date)
        assert order.ship_at == future_date.isoformat()

    def test_set_ship_at_past_date_raises_error(self, order):
        """Test that setting ship_at to past date raises ValueError."""
        past_date = dt.date.today() - dt.timedelta(days=1)
        with pytest.raises(ValueError, match="Ship at must be a date in the future"):
            order.set_ship_at(past_date)

    def test_set_ship_at_yesterday_raises_error(self, order):
        """Test that setting ship_at to yesterday raises ValueError."""
        today = dt.date.today() - dt.timedelta(days=1)
        with pytest.raises(ValueError, match="Ship at must be a date in the future"):
            order.set_ship_at(today)

    def test_set_ship_at_not_date_raises_error(self, order):
        """Test that setting non-date ship_at raises ValueError."""
        with pytest.raises(ValueError, match="Ship at must be a date in the future"):
            order.set_ship_at("2025-02-20")  # type: ignore

    def test_set_ship_at_datetime_raises_error(self, order):
        """Test that setting datetime instead of date raises ValueError."""
        with pytest.raises(TypeError, match="datetime"):
            order.set_ship_at(dt.datetime.now())  # type: ignore


class TestOrderDescriptionFieldValidation:
    """Tests for description field validation."""

    @pytest.fixture
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
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

    def test_description_required(self, minimal_order_data):
        """Test that description is required."""
        with pytest.raises(TypeError):
            Order(**minimal_order_data)

    def test_description_empty_raises_error(self, minimal_order_data):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="Description must be a non-empty string"):
            Order(description="", **minimal_order_data)

    def test_description_whitespace_only_raises_error(self, minimal_order_data):
        """Test that whitespace-only description raises ValueError."""
        with pytest.raises(ValueError, match="Description must be a non-empty string"):
            Order(description="   ", **minimal_order_data)

    def test_description_not_string_raises_error(self, minimal_order_data):
        """Test that non-string description raises ValueError."""
        with pytest.raises(ValueError, match="Description must be a non-empty string"):
            Order(description=123, **minimal_order_data)  # type: ignore

    def test_description_gets_stripped(self, minimal_order_data):
        """Test that whitespace around description is stripped."""
        order = Order(description="  Test Description  ", **minimal_order_data)
        assert order.description == "Test Description"

    def test_description_stored_as_member(self, minimal_order_data):
        """Test that description is stored as a member variable."""
        order = Order(description="Harman Order ORD-12345", **minimal_order_data)
        assert order.description == "Harman Order ORD-12345"


class TestOrderDeliveryInstructionsField:
    """Tests for delivery_instructions field."""

    @pytest.fixture
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_delivery_instructions_optional(self, minimal_order_data):
        """Test that delivery_instructions is optional with empty default."""
        order = Order(**minimal_order_data)
        assert order.delivery_instructions == ""

    def test_delivery_instructions_can_be_set(self, minimal_order_data):
        """Test that delivery_instructions can be set to a value."""
        instructions = "Please deliver on weekday between 8-17"
        order = Order(delivery_instructions=instructions, **minimal_order_data)
        assert order.delivery_instructions == instructions

    def test_delivery_instructions_gets_stripped(self, minimal_order_data):
        """Test that whitespace around delivery_instructions is stripped."""
        instructions = "  Please deliver between 9-5  "
        order = Order(delivery_instructions=instructions, **minimal_order_data)
        assert order.delivery_instructions == "Please deliver between 9-5"

    def test_delivery_instructions_not_string_raises_error(self, minimal_order_data):
        """Test that non-string delivery_instructions raises ValueError."""
        with pytest.raises(ValueError, match="Delivery instructions must be an instance of str"):
            Order(delivery_instructions=123, **minimal_order_data)  # type: ignore

    def test_delivery_instructions_empty_string_allowed(self, minimal_order_data):
        """Test that empty string is allowed for delivery_instructions."""
        order = Order(delivery_instructions="", **minimal_order_data)
        assert order.delivery_instructions == ""


class TestOrderImmutability:
    """Tests for Order immutability (frozen dataclass)."""

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
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

    def test_cannot_modify_ship_at_directly(self, order):
        """Test that ship_at cannot be modified directly."""
        with pytest.raises((AttributeError, TypeError)):
            order.ship_at = dt.date.today()

    def test_can_modify_via_setter_methods(self, order):
        """Test that settable fields can be modified via setter methods."""
        order.set_sale_id(999)
        assert order.sale_id == 999

        order.set_status(OrderStatus.SHIPPED)
        assert order.status == OrderStatus.SHIPPED

        future_date = dt.date.today() + dt.timedelta(days=5)
        order.set_ship_at(future_date)
        assert order.ship_at == future_date.isoformat()


class TestOrderEquality:
    """Tests for Order equality comparison."""

    @pytest.fixture
    def order_data(self):
        """Provide Order data for equality tests."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_not_equal_orders_with_same_data(self, order_data):
        """Test that orders with same data are not equal."""
        # Use same real objects
        ship_to = order_data["ship_to"]
        line_items = order_data["line_items"]

        order1 = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
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
            description="Test order",
            ship_to=ship_to,
            line_items=line_items,
        )

        assert order1 != order2

    def test_different_customer_ids_not_equal(self, order_data):
        """Test that orders with different customer IDs are not equal."""
        filtered_data = {
            k: v for k, v in order_data.items() if k not in ("customer_id", "description")
        }
        order1 = Order(customer_id=100, description="Test order", **filtered_data)
        order2 = Order(customer_id=200, description="Test order", **filtered_data)

        assert order1 != order2


class TestOrderSaleIDDefault:
    """Tests for sale_id field defaults."""

    @pytest.fixture
    def valid_order_data(self):
        """Provide valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_sale_id_defaults_to_zero(self, valid_order_data):
        """Test that sale_id defaults to 0."""
        order = Order(**valid_order_data)
        assert order.sale_id == 0

    def test_sale_id_cannot_be_initialized_directly(self, valid_order_data):
        """Test that sale_id cannot be passed as init parameter."""
        with pytest.raises(TypeError):
            Order(sale_id=999, **valid_order_data)  # type: ignore


class TestOrderStatusDefault:
    """Tests for status field defaults."""

    @pytest.fixture
    def valid_order_data(self):
        """Provide valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_status_defaults_to_new(self, valid_order_data):
        """Test that status defaults to OrderStatus.NEW."""
        order = Order(**valid_order_data)
        assert order.status == OrderStatus.NEW

    def test_status_cannot_be_initialized_directly(self, valid_order_data):
        """Test that status cannot be passed as init parameter."""
        with pytest.raises(TypeError):
            Order(status=OrderStatus.CREATED, **valid_order_data)  # type: ignore


class TestOrderCreatedAtDefault:
    """Tests for created_at field defaults."""

    @pytest.fixture
    def valid_order_data(self):
        """Provide valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_created_at_is_auto_generated(self, valid_order_data):
        """Test that created_at is automatically set."""
        before = dt.datetime.now()
        order = Order(**valid_order_data)
        after = dt.datetime.now()

        assert before <= dt.datetime.fromisoformat(order.created_at) <= after

    def test_created_at_is_datetime(self, valid_order_data):
        """Test that created_at is a datetime object."""
        order = Order(**valid_order_data)
        assert isinstance(dt.datetime.fromisoformat(order.created_at), dt.datetime)

    def test_created_at_cannot_be_initialized_directly(self, valid_order_data):
        """Test that created_at cannot be passed as init parameter."""
        with pytest.raises(TypeError):
            Order(created_at=dt.datetime.now(dt.UTC), **valid_order_data)  # type: ignore


class TestOrderShipAtDefault:
    """Tests for ship_at field defaults."""

    @pytest.fixture
    def valid_order_data(self):
        """Provide valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "administration_id": 1,
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_ship_at_defaults_to_seven_days_from_today(self, valid_order_data):
        """Test that ship_at defaults to 7 days from today."""
        order = Order(**valid_order_data)
        expected_date = dt.date.today() + dt.timedelta(days=7)
        assert order.ship_at == expected_date.isoformat()

    def test_ship_at_is_date(self, valid_order_data):
        """Test that ship_at is a date object."""
        order = Order(**valid_order_data)
        assert isinstance(dt.date.fromisoformat(order.ship_at), dt.date)
        assert "." not in order.ship_at  # Ensure it's a date, not datetime string

    def test_ship_at_cannot_be_initialized_directly(self, valid_order_data):
        """Test that ship_at cannot be passed as init parameter."""
        with pytest.raises(TypeError):
            Order(ship_at=dt.date.today() + dt.timedelta(days=5), **valid_order_data)  # type: ignore


class TestOrderAdministrationIDValidationMessages:
    """Tests for administration_id validation error messages."""

    @pytest.fixture
    def minimal_order_data(self):
        """Provide minimal valid Order data."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return {
            "customer_id": 100,
            "order_provider": "Provider",
            "pricelist_id": 50,
            "remote_order_id": "ORD-123",
            "shipment_type": "standard",
            "description": "Test order",
            "ship_to": ship_to,
            "line_items": [line_item],
        }

    def test_administration_id_error_message_format(self, minimal_order_data):
        """Test that error message ends with period."""
        with pytest.raises(ValueError, match="Administration ID must be a positive integer\\."):
            Order(administration_id=0, **minimal_order_data)


class TestOrderLargeQuantities:
    """Tests for Order with large quantities."""

    def test_order_with_large_line_item_quantities(self):
        """Test that Order can handle large quantities in line items."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=1000000)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )
        assert order.line_items[0].quantity == 1000000


class TestOrderMultipleLineItems:
    """Tests for Order with multiple line items."""

    def test_order_preserves_line_items_order(self):
        """Test that Order preserves the order of line items."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_items = [
            LineItem(line_id="RL-001", product_code="PROD-001", quantity=1),
            LineItem(line_id="RL-002", product_code="PROD-002", quantity=2),
            LineItem(line_id="RL-003", product_code="PROD-003", quantity=3),
        ]
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Provider",
            pricelist_id=50,
            remote_order_id="ORD-123",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=line_items,
        )
        assert order.line_items == line_items
        assert len(order.line_items) == 3


class TestOrderRepresentation:
    """Tests for Order string representation."""

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD-001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="ORD-12345",
            shipment_type="standard",
            description="Harman Order ORD-12345",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_repr_contains_class_name(self, order):
        """Test that repr contains Order class name."""
        repr_str = repr(order)
        assert "Order" in repr_str

    def test_repr_contains_remote_order_id(self, order):
        """Test that repr contains remote_order_id value."""
        repr_str = repr(order)
        assert "ORD-12345" in repr_str

    def test_description_property_format(self, order):
        """Test description property returns correct format."""
        assert order.description == "Harman Order ORD-12345"
