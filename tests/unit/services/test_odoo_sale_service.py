"""Unit tests for OdooSaleService."""

from datetime import date
from unittest.mock import Mock

import httpx
import pytest

from src.app.errors import SaleError
from src.app.odoo_auth import OdooAuth
from src.domain import LineItem, Order, ShipTo
from src.services.odoo_sale_service import OdooSaleService


class TestOdooSaleServiceInstantiation:
    """Tests for OdooSaleService instantiation."""

    @pytest.fixture
    def mock_auth(self):
        """Provide a mocked OdooAuth."""
        auth = Mock(spec=OdooAuth)
        auth.database = "test_db"
        auth.user_id = 1
        auth.password = "test_password"
        return auth

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked httpx.Client with base_url."""
        client = Mock(spec=httpx.Client)
        client.base_url = "http://localhost:8069"
        return client

    def test_instantiation_with_all_fields(self, mock_auth, mock_client):
        """Test creating OdooSaleService with all required fields."""
        service = OdooSaleService(auth=mock_auth, engine=mock_client)

        assert service.auth is mock_auth
        assert service.engine is mock_client

    def test_instantiation_raises_on_invalid_auth(self, mock_client):
        """Test that ValueError is raised with invalid auth."""
        with pytest.raises(ValueError, match="authentication information is missing or invalid"):
            OdooSaleService(auth=None, engine=mock_client)  # type: ignore

    def test_instantiation_raises_on_invalid_engine(self, mock_auth):
        """Test that ValueError is raised with invalid engine."""
        with pytest.raises(ValueError, match="engine is missing or invalid"):
            OdooSaleService(auth=mock_auth, engine=None)  # type: ignore

    def test_instantiation_raises_on_missing_base_url(self, mock_auth):
        """Test that ValueError is raised when base_url is not set."""
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = None
        with pytest.raises(ValueError, match="base URL is not set"):
            OdooSaleService(auth=mock_auth, engine=mock_client)

    def test_id_counter_initializes_correctly(self, mock_auth, mock_client):
        """Test that _id_counter is initialized as an iterator."""
        service = OdooSaleService(auth=mock_auth, engine=mock_client)

        assert next(service._id_counter) == 1
        assert next(service._id_counter) == 2


class TestGetSaleData:
    """Tests for _get_sale_data method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions="Handle with care",
            ship_to=ship_to,
            line_items=[line_item],
        )
        return order

    def test_get_sale_data_returns_sale_when_found(self, service, mocker, order):
        """Test that _get_sale_data returns sale data when found."""
        expected_sale = {"id": 100, "name": "SO-12345"}
        mocker.patch.object(OdooSaleService, "_call", return_value=[expected_sale])

        result = service._get_sale_data(order)

        assert result == expected_sale

    def test_get_sale_data_returns_empty_dict_when_not_found(self, service, mocker, order):
        """Test that _get_sale_data returns empty dict when not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service._get_sale_data(order)

        assert result == {}

    def test_get_sale_data_returns_empty_dict_on_invalid_result(self, service, mocker, order):
        """Test that _get_sale_data returns empty dict on invalid result."""
        mocker.patch.object(OdooSaleService, "_call", return_value="invalid")

        result = service._get_sale_data(order)

        assert result == {}


class TestIsSaleCreated:
    """Tests for is_sale_created method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions="Handle with care",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_is_sale_created_returns_true_when_sale_exists(self, service, mocker, order):
        """Test that is_sale_created returns True when sale exists."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 100})

        result = service.is_sale_created(order)

        assert result is True

    def test_is_sale_created_returns_false_when_sale_not_found(self, service, mocker, order):
        """Test that is_sale_created returns False when sale not found."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={})

        result = service.is_sale_created(order)

        assert result is False


class TestCreateSale:
    """Tests for create_sale method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions="Handle with care",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_ship_at(date(2027, 12, 25))
        return order

    def test_create_sale_successful(self, service, mocker, order):
        """Test successful sale creation."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={})
        mocker.patch.object(OdooSaleService, "_create_contact", return_value=10)
        mocker.patch.object(
            OdooSaleService,
            "_convert_order_lines",
            return_value=[{"product_id": 1, "quantity": 10}],
        )
        mocker.patch.object(OdooSaleService, "_get_carrier_id", return_value=5)
        mocker.patch.object(OdooSaleService, "_call", return_value=100)

        result = service.create_sale(order)

        assert result == 100

    def test_create_sale_returns_existing_sale_id(self, service, mocker, order):
        """Test that create_sale returns existing sale ID if already created."""
        existing_sale = {"id": 100}
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value=existing_sale)

        result = service.create_sale(order)

        assert result == 100

    def test_create_sale_raises_when_creation_fails(self, service, mocker, order):
        """Test that SaleError is raised when sale creation returns an int."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={})
        mocker.patch.object(OdooSaleService, "_create_contact", return_value=10)
        mocker.patch.object(OdooSaleService, "_convert_order_lines", return_value=[])
        mocker.patch.object(OdooSaleService, "_get_carrier_id", return_value=5)
        mocker.patch.object(OdooSaleService, "_call", return_value="100")

        with pytest.raises(SaleError, match="Failed to create sale"):
            service.create_sale(order)


class TestConfirmSale:
    """Tests for confirm_sale method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_confirm_sale_successful(self, service, mocker, order):
        """Test successful sale confirmation."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 100})
        mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.confirm_sale(order)

    def test_confirm_sale_raises_when_sale_not_found(self, service, mocker, order):
        """Test that SaleError is raised when sale not found."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={})

        with pytest.raises(SaleError, match="Cannot confirm non-existent sale"):
            service.confirm_sale(order)

    def test_confirm_sale_raises_on_confirmation_failure(self, service, mocker, order):
        """Test that SaleError is raised when confirmation fails."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 100})
        mocker.patch.object(OdooSaleService, "_call", return_value=False)

        with pytest.raises(SaleError, match="Failed to confirm sale"):
            service.confirm_sale(order)


class TestGetCompletedSales:
    """Tests for get_completed_sales method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    def test_get_completed_sales_returns_ids(self, service, mocker):
        """Test that get_completed_sales returns list of (id, remote_order_id) tuples."""
        mocker.patch.object(
            OdooSaleService,
            "_call",
            return_value=[
                {"id": 100, "x_remote_order_id": "HA-001"},
                {"id": 101, "x_remote_order_id": "HA-002"},
                {"id": 102, "x_remote_order_id": "HA-003"},
            ],
        )

        result = service.get_completed_sales("Harman")

        assert result == [(100, "HA-001"), (101, "HA-002"), (102, "HA-003")]

    def test_get_completed_sales_returns_empty_list_when_not_found(self, service, mocker):
        """Test that get_completed_sales returns empty list when not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service.get_completed_sales("Harman")

        assert result == []

    def test_get_completed_sales_returns_empty_list_on_invalid_result(self, service, mocker):
        """Test that get_completed_sales returns empty list on invalid result."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[100, "invalid"])

        result = service.get_completed_sales("Harman")

        assert result == []


class TestConvertOrderLines:
    """Tests for _convert_order_lines method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_convert_order_lines_successful(self, service, mocker, order):
        """Test successful order line conversion."""
        product_data = [{"id": 1, "name": "Product 1"}]
        mocker.patch.object(OdooSaleService, "_call", return_value=product_data)

        result = service._convert_order_lines(order)

        assert len(result) == 1
        assert result[0]["product_id"] == 1
        assert result[0]["name"] == "Product 1"
        assert result[0]["product_uom_qty"] == 10

    def test_convert_order_lines_raises_when_product_not_found(self, service, mocker, order):
        """Test that SaleError is raised when product is not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        with pytest.raises(SaleError, match="Product PROD001 not found"):
            service._convert_order_lines(order)

    def test_convert_order_lines_raises_on_invalid_product_data(self, service, mocker, order):
        """Test that SaleError is raised on invalid product data."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 1}])  # missing "name"

        with pytest.raises(SaleError, match="Product PROD001 not found"):
            service._convert_order_lines(order)

    def test_convert_order_lines_raises_when_product_is_not_dict(self, service, mocker, order):
        """Test that SaleError is raised when product is not a dict."""
        mocker.patch.object(OdooSaleService, "_call", return_value="not_a_dict")

        with pytest.raises(SaleError, match="Product PROD001 not found"):
            service._convert_order_lines(order)

    def test_convert_order_lines_raises_when_product_missing_id(self, service, mocker, order):
        """Test that SaleError is raised when product dict missing id field."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"name": "Product 1"}])

        with pytest.raises(SaleError, match="Product PROD001 not found"):
            service._convert_order_lines(order)


class TestGetCountryId:
    """Tests for _get_country_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    def test_get_country_id_successful(self, service, mocker):
        """Test successful country ID retrieval."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 42}])

        result = service._get_country_id("US")

        assert result == 42

    def test_get_country_id_strips_whitespace_and_uppercase(self, service, mocker):
        """Test that whitespace is stripped and code is uppercased."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 42}])

        result = service._get_country_id("  us  ")

        assert result == 42

    def test_get_country_id_handles_long_codes(self, service, mocker):
        """Test that country codes are truncated to 2 characters."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 42}])

        result = service._get_country_id("USA")

        assert result == 42

    def test_get_country_id_raises_when_not_found(self, service, mocker):
        """Test that SaleError is raised when country is not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        with pytest.raises(SaleError, match="Country code 'XX' not found"):
            service._get_country_id("XX")

    def test_get_country_id_raises_when_not_integer(self, service, mocker):
        """Test that TypeError is raised when country_id is not an integer."""
        mocker.patch.object(OdooSaleService, "_call_search_single", return_value="not_an_int")

        with pytest.raises(TypeError, match="country_id should be an integer"):
            service._get_country_id("US")

    def test_get_country_id_raises_when_id_is_string_numbers(self, service, mocker):
        """Test that TypeError is raised when country_id is string of numbers."""
        mocker.patch.object(OdooSaleService, "_call_search_single", return_value=42.5)

        with pytest.raises(TypeError, match="country_id should be an integer"):
            service._get_country_id("US")


class TestGetStateId:
    """Tests for _get_state_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    def test_get_state_id_successful(self, service, mocker):
        """Test successful state ID retrieval."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 123}])

        result = service._get_state_id(42, "California")

        assert result == 123

    def test_get_state_id_returns_zero_for_empty_state(self, service, mocker):
        """Test that 0 is returned for empty state."""
        spy = mocker.spy(OdooSaleService, "_call")

        result = service._get_state_id(42, "")

        assert result == 0
        spy.assert_not_called()

    def test_get_state_id_returns_zero_for_whitespace_state(self, service, mocker):
        """Test that 0 is returned for whitespace-only state."""
        spy = mocker.spy(OdooSaleService, "_call")

        result = service._get_state_id(42, "   ")

        assert result == 0
        spy.assert_not_called()

    def test_get_state_id_returns_zero_when_not_found(self, service, mocker):
        """Test that 0 is returned when state is not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service._get_state_id(42, "NonExistent")

        assert result == 0

    def test_get_state_id_raises_when_not_integer(self, service, mocker):
        """Test that TypeError is raised when state_id is not an integer."""
        mocker.patch.object(OdooSaleService, "_call_search_single", return_value="not_an_int")

        with pytest.raises(TypeError, match="state_id should be an integer"):
            service._get_state_id(42, "California")

    def test_get_state_id_raises_when_id_is_float(self, service, mocker):
        """Test that TypeError is raised when state_id is a float."""
        mocker.patch.object(OdooSaleService, "_call_search_single", return_value=123.45)

        with pytest.raises(TypeError, match="state_id should be an integer"):
            service._get_state_id(42, "California")


class TestGetCarrierId:
    """Tests for _get_carrier_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="FedEx",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_get_carrier_id_successful(self, service, mocker, order):
        """Test successful carrier ID retrieval."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 5}])

        result = service._get_carrier_id(order)

        assert result == 5

    def test_get_carrier_id_raises_for_empty_carrier_name(self, service, mocker):
        """Test that ValueError is raised for empty carrier name."""
        order = Mock()
        order.shipment_type = ""

        with pytest.raises(ValueError, match="Shipment type is required in order"):
            service._get_carrier_id(order)

    def test_get_carrier_id_raises_when_not_found(self, service, mocker, order):
        """Test that SaleError is raised when carrier is not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        with pytest.raises(SaleError, match="Carrier 'FedEx' not found"):
            service._get_carrier_id(order)

    def test_get_carrier_id_raises_when_not_integer(self, service, mocker, order):
        """Test that TypeError is raised when carrier_id is not an integer."""
        mocker.patch.object(OdooSaleService, "_call_search_single", return_value="not_an_int")

        with pytest.raises(TypeError, match="carrier_id should be an integer"):
            service._get_carrier_id(order)

    def test_get_carrier_id_raises_when_id_is_boolean(self, service, mocker, order):
        """Test that TypeError is raised when carrier_id is a non-int type."""
        mocker.patch.object(OdooSaleService, "_call_search_single", return_value=[1, 2])

        with pytest.raises(TypeError, match="carrier_id should be an integer"):
            service._get_carrier_id(order)


class TestGetContactDataFromOrder:
    """Tests for _get_contact_data_from_order method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self):
        """Provide an Order with ShipTo."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            company_name="ACME Corp",
            email="john@acme.com",
            phone="555-1234",
            street1="123 Main St",
            street2="Apt 4",
            city="San Francisco",
            postal_code="94102",
            country_code="US",
            state="California",
        )
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=5)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )
        return order

    def test_get_contact_data_from_order_successful(self, service, mocker, order):
        """Test successful contact data building."""
        mocker.patch.object(OdooSaleService, "_get_country_id", return_value=42)
        mocker.patch.object(OdooSaleService, "_get_state_id", return_value=100)

        result = service._get_contact_data_from_order(order)

        assert result["name"] == "John Doe"
        assert result["company_name"] == "ACME Corp"
        assert result["country_id"] == 42
        assert result["state_id"] == 100
        assert result["parent_id"] == 100
        assert result["company_id"] == 1
        assert result["ref"] == "CUST123"

    def test_get_contact_data_from_order_handles_missing_state(self, service, mocker):
        """Test that missing state is handled correctly."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            company_name="ACME Corp",
            email="john@acme.com",
            phone="555-1234",
            street1="123 Main St",
            street2="Apt 4",
            city="San Francisco",
            postal_code="94102",
            country_code="US",
            state="",
        )
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=5)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )
        mocker.patch.object(OdooSaleService, "_get_country_id", return_value=42)

        result = service._get_contact_data_from_order(order)

        assert result["state_id"] is None


class TestCreateContact:
    """Tests for _create_contact method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            company_name="ACME Corp",
            email="john@acme.com",
            phone="555-1234",
            street1="123 Main St",
            street2="",
            city="San Francisco",
            postal_code="94102",
            country_code="US",
            state="California",
        )
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_create_contact_successful(self, service, mocker, order):
        """Test successful contact creation."""
        mocker.patch.object(OdooSaleService, "_get_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", side_effect=[[], 10])

        result = service._create_contact(order)

        assert result == 10

    def test_create_contact_returns_existing_contact(self, service, mocker, order):
        """Test that existing contact is returned if found."""
        mocker.patch.object(OdooSaleService, "_get_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 10}])

        result = service._create_contact(order)

        assert result == 10

    def test_create_contact_raises_on_failure(self, service, mocker, order):
        """Test that SaleError is raised when contact creation fails."""
        mocker.patch.object(OdooSaleService, "_get_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", side_effect=[[], "not_an_int"])

        with pytest.raises(SaleError, match="Failed to create contact"):
            service._create_contact(order)


class TestUpdateContact:
    """Tests for update_contact method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            company_name="ACME Corp",
            email="john@acme.com",
            phone="555-1234",
            street1="123 Main St",
            street2="",
            city="San Francisco",
            postal_code="94102",
            country_code="US",
            state="California",
        )
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=5)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_update_contact_successful(self, service, mocker, order):
        """Test successful contact update."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100, "partner_shipping_id": [10, "Shipping Address"]},
        )
        mocker.patch.object(OdooSaleService, "_get_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.update_contact(order)

    def test_update_contact_raises_when_sale_not_found(self, service, mocker, order):
        """Test that SaleError is raised when sale is not found."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={})

        with pytest.raises(SaleError, match="Cannot update contact for non-existent sale"):
            service.update_contact(order)

    def test_update_contact_raises_when_no_shipping_contact(self, service, mocker, order):
        """Test that SaleError is raised when sale has no shipping contact."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 100})

        with pytest.raises(SaleError, match="Sale has no shipping contact to update"):
            service.update_contact(order)

    def test_update_contact_raises_on_write_failure(self, service, mocker, order):
        """Test that SaleError is raised when write fails."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100, "partner_shipping_id": [10, "Shipping Address"]},
        )
        mocker.patch.object(OdooSaleService, "_get_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", return_value=False)

        with pytest.raises(SaleError, match="Failed to update contact"):
            service.update_contact(order)


class TestHasExpectedOrderLines:
    """Tests for has_expected_order_lines method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@acme.com",
            phone="555-1234",
            street1="123 Main St",
            city="San Francisco",
            postal_code="94102",
            country_code="US",
        )
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )
        return order

    def test_has_expected_order_lines_success(self, service, mocker, order):
        """Test successful order line verification."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100, "order_line": [1, 2]},
        )
        mocker.patch.object(
            OdooSaleService,
            "_call",
            return_value=[{"product_id": [1, "[PROD001] Product Name"], "product_uom_qty": 10}],
        )
        mocker.patch.object(
            OdooSaleService,
            "_convert_order_lines",
            return_value=[{"product_id": 1, "product_uom_qty": 10}],
        )

        result = service.has_expected_order_lines(order)

        assert result is True

    def test_has_expected_order_lines_fails_for_mismatched_quantities(self, service, mocker, order):
        """Test that verification fails for mismatched quantities."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100, "order_line": [1]},
        )
        mocker.patch.object(
            OdooSaleService,
            "_call",
            return_value=[{"product_id": [1, "[PROD001] Product Name"], "product_uom_qty": 20}],
        )
        mocker.patch.object(
            OdooSaleService,
            "_convert_order_lines",
            return_value=[{"product_id": 1, "product_uom_qty": 10}],
        )

        result = service.has_expected_order_lines(order)

        assert result is False

    def test_has_expected_order_lines_raises_when_sale_not_found(self, service, mocker, order):
        """Test that SaleError is raised when sale not found."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={})

        with pytest.raises(SaleError, match="Cannot check order lines"):
            service.has_expected_order_lines(order)


class TestGetShippingInfo:
    """Tests for get_shipping_info method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self):
        """Provide an Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@acme.com",
            phone="555-1234",
            street1="123 Main St",
            city="San Francisco",
            postal_code="94102",
            country_code="US",
        )
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )
        return order

    def test_get_shipping_info_successful(self, service, mocker, order):
        """Test successful shipping info retrieval."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100, "company_id": 1},
        )
        mocker.patch.object(
            OdooSaleService,
            "_call",
            return_value=[
                {
                    "carrier_id": [5, "FedEx"],
                    "carrier_tracking_ref": "TRACK123",
                    "carrier_tracking_url": "http://track.fedex.com/TRACK123",
                    "partner_id": [10, "John Doe"],
                    "weight": 5.5,
                }
            ],
        )

        result = service.get_shipping_info(order)

        assert len(result) == 1
        assert result[0]["carrier"] == "FedEx"
        assert result[0]["carrier_tracking_ref"] == "TRACK123"
        assert result[0]["weight"] == 5.5

    def test_get_shipping_info_raises_error_when_not_found(self, service, mocker, order):
        """Test that SaleError is raised when no shipping info found."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100, "company_id": 1},
        )
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        with pytest.raises(SaleError, match="No shipping information found"):
            service.get_shipping_info(order)


class TestGetSerialsByLineItem:
    """Tests for get_serials_by_line_item method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=2)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_get_serials_by_line_item_returns_serials(self, service, mocker, order):
        """Test successful serial number retrieval by line item."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 100})
        mocker.patch.object(
            OdooSaleService,
            "_call",
            return_value=[
                {"product_id": [1, "[PROD001] Product A"], "serial": "SN001"},
                {"product_id": [1, "[PROD001] Product A"], "serial": "SN002"},
            ],
        )

        result = service.get_serials_by_line_item(order)

        assert result["LINE001"] == ["SN001", "SN002"]

    def test_get_serials_by_line_item_returns_dict_when_not_found(self, service, mocker, order):
        """Test that dict with empty lists is returned when no serials found."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 100})
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service.get_serials_by_line_item(order)

        assert len(result) == 1
        assert result["LINE001"] == []

    def test_get_serials_by_line_item_returns_dict_on_invalid_result(self, service, mocker, order):
        """Test that empty dict is returned on invalid result."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 100})
        mocker.patch.object(OdooSaleService, "_call", return_value="invalid")

        result = service.get_serials_by_line_item(order)

        assert len(result) == 1
        assert result["LINE001"] == []


class TestCall:
    """Tests for _call method."""

    @pytest.fixture
    def mock_auth(self):
        """Provide a mocked OdooAuth."""
        auth = Mock(spec=OdooAuth)
        auth.database = "test_db"
        auth.user_id = 1
        auth.password = "test_password"
        return auth

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked httpx.Client with base_url."""
        client = Mock(spec=httpx.Client)
        client.base_url = "http://localhost:8069"
        return client

    @pytest.fixture
    def service(self, mock_auth, mock_client):
        """Provide an OdooSaleService instance."""
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    def test_call_successful(self, service, mock_client):
        """Test successful JSON-RPC call."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": 100, "id": 1}
        mock_client.post.return_value = mock_response

        result = service._call("sale.order", "create", query_data=[{}])

        assert result == 100
        mock_client.post.assert_called_once()

    def test_call_raises_on_http_error(self, service, mock_client):
        """Test that HTTP errors are raised."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=Mock(), response=mock_response
        )
        mock_client.post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            service._call("sale.order", "create")

    def test_call_raises_on_json_rpc_error(self, service, mock_client):
        """Test that SaleError is raised for JSON-RPC errors."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "error": {
                "message": "Record not found",
                "code": 1,
                "data": "detail",
            },
            "id": 1,
        }
        mock_client.post.return_value = mock_response

        with pytest.raises(SaleError, match="Odoo JSON-RPC error"):
            service._call("sale.order", "read")

    def test_call_uses_query_options(self, service, mock_client):
        """Test that query_options are included in the payload."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": [], "id": 1}
        mock_client.post.return_value = mock_response

        service._call(
            "sale.order",
            "search_read",
            query_data=[[["id", "=", 100]]],
            query_options={"limit": 1},
        )

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["args"][6] == {"limit": 1}

    def test_call_increments_id_counter(self, service, mock_client):
        """Test that ID counter is incremented for each call."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": None, "id": 1}
        mock_client.post.return_value = mock_response

        service._call("sale.order", "create")
        service._call("sale.order", "create")

        calls = mock_client.post.call_args_list
        id_1 = calls[0][1]["json"]["id"]
        id_2 = calls[1][1]["json"]["id"]
        assert id_2 > id_1


class TestOdooSaleServiceCallSearchSingle:
    """Tests for _call_search_single method."""

    @pytest.fixture
    def mock_auth(self):
        """Provide a mocked OdooAuth."""
        auth = Mock(spec=OdooAuth)
        auth.database = "test_db"
        auth.user_id = 1
        auth.password = "test_password"
        return auth

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked httpx.Client with base_url."""
        client = Mock(spec=httpx.Client)
        client.base_url = "http://test.example.com"
        return client

    @pytest.fixture
    def service(self, mock_auth, mock_client):
        """Provide a configured OdooSaleService."""
        return OdooSaleService(auth=mock_auth, engine=mock_client)

    def test_call_search_single_with_missing_fields(self, service, mock_client):
        """Test _call_search_single raises when requested fields are missing."""
        # Mock response missing a requested field
        mock_client.post.return_value = Mock(
            json=lambda: {
                "jsonrpc": "2.0",
                "result": [{"id": 100, "name": "Test"}],  # missing 'state' field
            }
        )

        with pytest.raises(SaleError, match="Partner not found"):
            service._call_search_single(
                model="res.partner",
                query_data=[["id", "=", 100]],
                fields=["id", "name", "state"],
                error_message="Partner not found",
            )

    def test_call_search_single_with_all_fields_present(self, service, mock_client):
        """Test _call_search_single succeeds when all requested fields are present."""
        mock_client.post.return_value = Mock(
            json=lambda: {
                "jsonrpc": "2.0",
                "result": [{"id": 100, "name": "Test Company", "email": "test@example.com"}],
            }
        )

        result = service._call_search_single(
            model="res.partner",
            query_data=[["id", "=", 100]],
            fields=["id", "name", "email"],
        )

        assert isinstance(result, dict)
        assert result["id"] == 100
        assert result["name"] == "Test Company"

    def test_call_search_single_with_empty_result(self, service, mock_client):
        """Test _call_search_single returns None for empty results when no error message."""
        mock_client.post.return_value = Mock(json=lambda: {"jsonrpc": "2.0", "result": []})

        result = service._call_search_single(
            model="res.partner",
            query_data=[["id", "=", 999]],
            fields=["id"],
        )

        assert result is None

    def test_call_search_single_with_id_field_only(self, service, mock_client):
        """Test _call_search_single returns integer when only id field requested."""
        mock_client.post.return_value = Mock(
            json=lambda: {
                "jsonrpc": "2.0",
                "result": [{"id": 100}],
            }
        )

        result = service._call_search_single(
            model="res.partner",
            query_data=[["id", "=", 100]],
            fields=["id"],
        )

        assert isinstance(result, int)
        assert result == 100

    def test_call_search_single_returns_none_when_multi_field_missing(self, service, mock_client):
        """Test _call_search_single returns None when multi-field request has missing fields."""
        mock_client.post.return_value = Mock(
            json=lambda: {
                "jsonrpc": "2.0",
                "result": [{"id": 100, "name": "Test"}],  # Missing "email" field
            }
        )

        result = service._call_search_single(
            model="res.partner",
            query_data=[["id", "=", 100]],
            fields=["id", "name", "email"],
        )

        # Should return None because email field is missing and no error_message
        assert result is None

    def test_call_search_single_raises_on_missing_field_with_error(self, service, mock_client):
        """Test _call_search_single raises when field missing and error_message set."""
        mock_client.post.return_value = Mock(
            json=lambda: {
                "jsonrpc": "2.0",
                "result": [{"id": 100}],  # Missing "name" field
            }
        )

        with pytest.raises(SaleError, match="Partner not found"):
            service._call_search_single(
                model="res.partner",
                query_data=[["id", "=", 100]],
                fields=["id", "name"],
                error_message="Partner not found",
            )


class TestUpdateDeliveryInstructions:
    """Tests for update_delivery_instructions method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        mock_client.base_url = "http://localhost:8069"
        return OdooSaleService(auth=mock_auth, engine=mock_client)

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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions="Handle with care",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_update_delivery_instructions_successful(self, service, mocker, order):
        """Test successful delivery instructions update."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100},
        )
        mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.update_delivery_instructions(order)

    def test_update_delivery_instructions_returns_early_on_empty_instructions(
        self, service, mocker
    ):
        """Test that update returns early when delivery instructions are empty."""
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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order_empty = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions="",
            ship_to=ship_to,
            line_items=[line_item],
        )
        get_sale_spy = mocker.spy(OdooSaleService, "_get_sale_data")
        call_spy = mocker.spy(OdooSaleService, "_call")

        service.update_delivery_instructions(order_empty)

        get_sale_spy.assert_not_called()
        call_spy.assert_not_called()

    def test_update_delivery_instructions_returns_early_on_whitespace_instructions(
        self, service, mocker
    ):
        """Test that update returns early when delivery instructions are whitespace only."""
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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order_whitespace = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions="   \t  \n  ",
            ship_to=ship_to,
            line_items=[line_item],
        )
        get_sale_spy = mocker.spy(OdooSaleService, "_get_sale_data")
        call_spy = mocker.spy(OdooSaleService, "_call")

        service.update_delivery_instructions(order_whitespace)

        get_sale_spy.assert_not_called()
        call_spy.assert_not_called()

    def test_update_delivery_instructions_raises_when_sale_not_found(self, service, mocker, order):
        """Test that SaleError is raised when sale is not found."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={})

        with pytest.raises(
            SaleError, match="Cannot update delivery instructions for non-existent sale"
        ):
            service.update_delivery_instructions(order)

    def test_update_delivery_instructions_raises_when_sale_id_is_zero(self, service, mocker, order):
        """Test that SaleError is raised when sale ID is 0."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"id": 0})

        with pytest.raises(
            SaleError, match="Cannot update delivery instructions for non-existent sale"
        ):
            service.update_delivery_instructions(order)

    def test_update_delivery_instructions_raises_when_sale_missing_id_field(
        self, service, mocker, order
    ):
        """Test that SaleError is raised when sale data missing id field."""
        mocker.patch.object(OdooSaleService, "_get_sale_data", return_value={"name": "SO-123"})

        with pytest.raises(
            SaleError, match="Cannot update delivery instructions for non-existent sale"
        ):
            service.update_delivery_instructions(order)

    def test_update_delivery_instructions_raises_on_write_failure(self, service, mocker, order):
        """Test that SaleError is raised when write fails."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100},
        )
        mocker.patch.object(OdooSaleService, "_call", return_value=False)

        with pytest.raises(SaleError, match="Failed to update delivery instructions for sale 100"):
            service.update_delivery_instructions(order)

    def test_update_delivery_instructions_calls_with_correct_parameters(
        self, service, mocker, order
    ):
        """Test that _call is invoked with correct parameters."""
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100},
        )
        call_mock = mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.update_delivery_instructions(order)

        call_mock.assert_called_once()
        call_args = call_mock.call_args
        assert call_args[1]["model"] == "sale.order"
        assert call_args[1]["method"] == "write"
        assert call_args[1]["query_data"] == [
            [100],
            {"x_remote_delivery_instructions": "Handle with care"},
        ]

    def test_update_delivery_instructions_handles_long_instructions(self, service, mocker):
        """Test that long delivery instructions are handled correctly."""
        long_instructions = "A" * 1000
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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order_long = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions=long_instructions,
            ship_to=ship_to,
            line_items=[line_item],
        )
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100},
        )
        call_mock = mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.update_delivery_instructions(order_long)

        call_args = call_mock.call_args
        assert call_args[1]["query_data"][1]["x_remote_delivery_instructions"] == long_instructions

    def test_update_delivery_instructions_handles_special_characters(self, service, mocker):
        """Test that delivery instructions with special characters are handled correctly."""
        special_instructions = (
            "Handle with care! Include \n newlines and 'quotes' and \"double quotes\""
        )
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
        line_item = LineItem(remote_line_id="LINE001", product_code="PROD001", quantity=10)
        order_special = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            delivery_instructions=special_instructions,
            ship_to=ship_to,
            line_items=[line_item],
        )
        mocker.patch.object(
            OdooSaleService,
            "_get_sale_data",
            return_value={"id": 100},
        )
        call_mock = mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.update_delivery_instructions(order_special)

        call_args = call_mock.call_args
        assert (
            call_args[1]["query_data"][1]["x_remote_delivery_instructions"] == special_instructions
        )
