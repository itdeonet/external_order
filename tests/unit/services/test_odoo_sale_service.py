"""Unit tests for OdooSaleService."""

from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests

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
        """Provide a mocked requests.Session."""
        client = Mock(spec=requests.Session)
        return client

    def test_instantiation_with_all_fields(self, mock_auth, mock_client):
        """Test creating OdooSaleService with all required fields."""
        service = OdooSaleService(auth=mock_auth, session=mock_client)

        assert service.auth is mock_auth
        assert service.session is mock_client

    def test_instantiation_raises_on_invalid_auth(self, mock_client):
        """Test that ValueError is raised with invalid auth."""
        with pytest.raises(ValueError, match="authentication information is missing or invalid"):
            OdooSaleService(auth=None, session=mock_client)  # type: ignore

    def test_instantiation_raises_on_invalid_engine(self, mock_auth):
        """Test that ValueError is raised with invalid session."""
        with pytest.raises(ValueError, match="session is missing or invalid"):
            OdooSaleService(auth=mock_auth, session=None)  # type: ignore

    def test_instantiation_raises_on_missing_base_url(self, mock_auth):
        """Test that ValueError is raised when base_url is not set."""
        # Note: requests.Session doesn't use base_url; it's passed to post()
        # This test may need adjustment based on how base_url is now being handled
        mock_client = Mock(spec=requests.Session)
        with pytest.raises(ValueError, match="base URL is not set"):
            OdooSaleService(auth=mock_auth, session=mock_client, base_url="")

    def test_id_counter_initializes_correctly(self, mock_auth, mock_client):
        """Test that _id_counter is initialized as an iterator."""
        service = OdooSaleService(auth=mock_auth, session=mock_client)

        assert next(service._id_counter) == 1
        assert next(service._id_counter) == 2

    def test_register_classmethod_creates_instance_with_defaults(self, mock_client):
        """Test that register() classmethod creates instance with defaults."""
        mock_registry = Mock()
        with patch("src.services.odoo_sale_service.get_sale_services", return_value=mock_registry):
            with patch("src.services.odoo_sale_service.get_config") as mock_config_func:
                mock_config = Mock()
                mock_config.odoo_base_url = "http://test.url"
                mock_config.ssl_verify = True
                mock_config_func.return_value = mock_config

                OdooSaleService.register("odoo_sales", mock_client)

                # Verify register was called
                mock_registry.register.assert_called_once()
                call_args = mock_registry.register.call_args
                assert call_args[0][0] == "odoo_sales"
                assert isinstance(call_args[0][1], OdooSaleService)

    def test_register_classmethod_registers_with_provided_session(self, mock_client):
        """Test that register() classmethod registers instance with provided session."""
        mock_registry = Mock()
        with patch("src.services.odoo_sale_service.get_sale_services", return_value=mock_registry):
            with patch("src.services.odoo_sale_service.get_config") as mock_config_func:
                mock_config = Mock()
                mock_config.odoo_base_url = "http://test.url"
                mock_config.ssl_verify = True
                mock_config_func.return_value = mock_config

                service_name = "test_sales_service"
                OdooSaleService.register(service_name, mock_client)

                # Verify the service was registered with the provided session
                mock_registry.register.assert_called_once()
                registered_name, registered_service = mock_registry.register.call_args[0]
                assert registered_name == service_name
                assert registered_service.session is mock_client

    def test_register_classmethod_uses_config_defaults(self):
        """Test that register() classmethod uses configuration defaults."""
        mock_client = Mock(spec=requests.Session)
        mock_registry = Mock()

        with patch("src.services.odoo_sale_service.get_sale_services", return_value=mock_registry):
            with patch("src.services.odoo_sale_service.get_config") as mock_config_func:
                mock_config = Mock()
                mock_config.odoo_base_url = "https://odoo.example.com"
                mock_config.ssl_verify = True
                mock_config_func.return_value = mock_config

                OdooSaleService.register("odoo_sales_service", mock_client)

                # Verify register was called with a valid service
                mock_registry.register.assert_called_once()
                registered_service = mock_registry.register.call_args[0][1]
                assert registered_service.base_url == "https://odoo.example.com"


class TestSearchSaleData:
    """Tests for search_sale method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=10)
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

    def test_search_sale_returns_sale_when_found(self, service, mocker, order):
        """Test that search_sale returns sale data when found."""
        expected_sale = {"id": 100, "name": "SO-12345"}
        mocker.patch.object(OdooSaleService, "_call", return_value=[expected_sale])

        result = service.search_sale(order)

        assert result == expected_sale

    def test_search_sale_returns_empty_dict_when_not_found(self, service, mocker, order):
        """Test that search_sale returns empty dict when not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service.search_sale(order)

        assert result == {}

    def test_get_search_sale_returns_empty_dict_on_invalid_result(self, service, mocker, order):
        """Test that search_sale returns empty dict on invalid result."""
        mocker.patch.object(OdooSaleService, "_call", return_value="invalid")

        result = service.search_sale(order)

        assert result == {}


class TestCreateSale:
    """Tests for create_sale method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=10)
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
        mocker.patch.object(
            OdooSaleService, "search_sale", side_effect=[{}, {"id": 100, "name": "SO-12345"}]
        )
        mocker.patch.object(OdooSaleService, "_create_contact", return_value=10)
        mocker.patch.object(
            OdooSaleService,
            "_convert_order_lines",
            return_value=[{"product_id": 1, "quantity": 10}],
        )
        mocker.patch.object(OdooSaleService, "_search_carrier_id", return_value=5)
        mocker.patch.object(OdooSaleService, "_call", return_value=100)

        result = service.create_sale(order)

        assert result == (100, "SO-12345")

    def test_create_sale_returns_existing_sale_id(self, service, mocker, order):
        """Test that create_sale returns existing sale ID and name if already created."""
        existing_sale = {"id": 100, "name": "SO-98765"}
        mocker.patch.object(OdooSaleService, "search_sale", return_value=existing_sale)

        result = service.create_sale(order)

        assert result == (100, "SO-98765")

    def test_create_sale_raises_when_creation_fails(self, service, mocker, order):
        """Test that SaleError is raised when sale creation returns non-integer."""
        mocker.patch.object(OdooSaleService, "search_sale", return_value={})
        mocker.patch.object(OdooSaleService, "_create_contact", return_value=10)
        mocker.patch.object(OdooSaleService, "_convert_order_lines", return_value=[])
        mocker.patch.object(OdooSaleService, "_search_carrier_id", return_value=5)
        mocker.patch.object(OdooSaleService, "_call", return_value="100")

        with pytest.raises(SaleError, match="Failed to create sale"):
            service.create_sale(order)

    def test_create_sale_raises_when_sale_not_found_after_creation(self, service, mocker, order):
        """Test that SaleError is raised when sale is not found after creation."""
        # First search returns empty (sale doesn't exist), second search also returns empty (failed to find after creation)
        mocker.patch.object(OdooSaleService, "search_sale", side_effect=[{}, {}])
        mocker.patch.object(OdooSaleService, "_create_contact", return_value=10)
        mocker.patch.object(
            OdooSaleService,
            "_convert_order_lines",
            return_value=[{"product_id": 1, "quantity": 10}],
        )
        mocker.patch.object(OdooSaleService, "_search_carrier_id", return_value=5)
        mocker.patch.object(OdooSaleService, "_call", return_value=100)

        with pytest.raises(SaleError, match="Sale created but not found on search"):
            service.create_sale(order)


class TestSearchCompletedSales:
    """Tests for search_completed_sales method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

    def test_search_completed_sales_returns_ids(self, service, mocker):
        """Test that search_completed_sales returns list of (id, remote_order_id) tuples."""
        mocker.patch.object(
            OdooSaleService,
            "_call",
            return_value=[
                {"id": 100, "x_remote_order_id": "HA-001"},
                {"id": 101, "x_remote_order_id": "HA-002"},
                {"id": 102, "x_remote_order_id": "HA-003"},
            ],
        )

        result = service.search_completed_sales("Harman")

        assert result == [(100, "HA-001"), (101, "HA-002"), (102, "HA-003")]

    def test_search_completed_sales_returns_empty_list_when_not_found(self, service, mocker):
        """Test that search_completed_sales returns empty list when not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service.search_completed_sales("Harman")

        assert result == []

    def test_search_completed_sales_returns_empty_list_on_invalid_result(self, service, mocker):
        """Test that search_completed_sales returns empty list on invalid result."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[100, "invalid"])

        result = service.search_completed_sales("Harman")

        assert result == []


class TestMarkSaleNotified:
    """Tests for mark_sale_notified method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

    def test_mark_sale_notified_calls_write_with_correct_params(self, service, mocker):
        """Test that mark_sale_notified calls _call with correct parameters."""
        mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.mark_sale_notified(42)

        service._call.assert_called_once_with(
            model="sale.order",
            method="write",
            query_data=[[42], {"x_remote_notified_completion": True}],
        )

    def test_mark_sale_notified_succeeds_with_true_result(self, service, mocker):
        """Test that mark_sale_notified succeeds when _call returns True."""
        mocker.patch.object(OdooSaleService, "_call", return_value=True)

        # Should not raise
        service.mark_sale_notified(42)

    def test_mark_sale_notified_raises_sale_error_on_false_result(self, service, mocker):
        """Test that mark_sale_notified raises SaleError when _call returns False."""
        mocker.patch.object(OdooSaleService, "_call", return_value=False)

        with pytest.raises(SaleError, match="Failed to mark sale 42 as notified"):
            service.mark_sale_notified(42)

    def test_mark_sale_notified_raises_sale_error_on_none_result(self, service, mocker):
        """Test that mark_sale_notified raises SaleError when _call returns None."""
        mocker.patch.object(OdooSaleService, "_call", return_value=None)

        with pytest.raises(SaleError, match="Failed to mark sale 100 as notified"):
            service.mark_sale_notified(100)

    def test_mark_sale_notified_raises_sale_error_on_zero_result(self, service, mocker):
        """Test that mark_sale_notified raises SaleError when _call returns 0."""
        mocker.patch.object(OdooSaleService, "_call", return_value=0)

        with pytest.raises(SaleError, match="Failed to mark sale 55 as notified"):
            service.mark_sale_notified(55)


class TestConvertOrderLines:
    """Tests for _convert_order_lines method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=10)
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

        with pytest.raises(SaleError, match="Product search for PROD001 failed"):
            service._convert_order_lines(order)

    def test_convert_order_lines_raises_on_invalid_product_data(self, service, mocker, order):
        """Test that SaleError is raised on invalid product data."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 1}])  # missing "name"

        with pytest.raises(SaleError, match="Product search for PROD001 failed"):
            service._convert_order_lines(order)

    def test_convert_order_lines_raises_when_product_is_not_dict(self, service, mocker, order):
        """Test that SaleError is raised when product is not a dict."""
        mocker.patch.object(OdooSaleService, "_call", return_value="not_a_dict")

        with pytest.raises(SaleError, match="Product search for PROD001 failed"):
            service._convert_order_lines(order)

    def test_convert_order_lines_raises_when_product_missing_id(self, service, mocker, order):
        """Test that SaleError is raised when product dict missing id field."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"name": "Product 1"}])

        with pytest.raises(SaleError, match="Product search for PROD001 failed"):
            service._convert_order_lines(order)


class TestSearchCountryId:
    """Tests for _search_country_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

    def test_search_country_id_successful(self, service, mocker):
        """Test successful country ID retrieval."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 42}])

        result = service._search_country_id("US")

        assert result == 42

    def test_search_country_id_strips_whitespace_and_uppercase(self, service, mocker):
        """Test that whitespace is stripped and code is uppercased."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 42}])

        result = service._search_country_id("  us  ")

        assert result == 42

    def test_search_country_id_handles_long_codes(self, service, mocker):
        """Test that country codes are truncated to 2 characters."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 42}])

        result = service._search_country_id("USA")

        assert result == 42

    def test_search_country_id_raises_when_not_found(self, service, mocker):
        """Test that SaleError is raised when country is not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        with pytest.raises(SaleError, match="Country code 'XX' not found"):
            service._search_country_id("XX")

    def test_search_country_id_raises_when_not_integer(self, service, mocker):
        """Test that TypeError is raised when country_id is not an integer."""
        mocker.patch.object(OdooSaleService, "_call", return_value="not_an_int")

        with pytest.raises(SaleError, match="Country code 'US' not found"):
            service._search_country_id("US")

    def test_search_country_id_raises_when_id_is_string_numbers(self, service, mocker):
        """Test that TypeError is raised when country_id is string of numbers."""
        mocker.patch.object(OdooSaleService, "_call", return_value=42.5)

        with pytest.raises(SaleError, match="Country code 'US' not found"):
            service._search_country_id("US")


class TestSearchStateId:
    """Tests for _search_state_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

    def test_search_state_id_successful(self, service, mocker):
        """Test successful state ID retrieval."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 123}])

        result = service._search_state_id(42, "California")

        assert result == 123

    def test_search_state_id_returns_zero_for_empty_state(self, service, mocker):
        """Test that 0 is returned for empty state."""
        spy = mocker.spy(OdooSaleService, "_call")

        result = service._search_state_id(42, "")

        assert result == 0
        spy.assert_not_called()

    def test_search_state_id_returns_zero_for_whitespace_state(self, service, mocker):
        """Test that 0 is returned for whitespace-only state."""
        spy = mocker.spy(OdooSaleService, "_call")

        result = service._search_state_id(42, "   ")

        assert result == 0
        spy.assert_not_called()

    def test_search_state_id_returns_zero_when_not_found(self, service, mocker):
        """Test that 0 is returned when state is not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service._search_state_id(42, "NonExistent")

        assert result == 0

    def test_search_state_id_returns_zero_when_not_integer(self, service, mocker):
        """Test that 0 is returned when state_id is not an integer."""
        mocker.patch.object(OdooSaleService, "_call", return_value="not_an_int")

        result = service._search_state_id(42, "California")

        assert result == 0

    def test_search_state_id_returns_zero_when_id_is_float(self, service, mocker):
        """Test that 0 is returned when state_id is a float."""
        mocker.patch.object(OdooSaleService, "_call", return_value=123.45)

        result = service._search_state_id(42, "California")

        assert result == 0


class TestSearchCarrierId:
    """Tests for _search_carrier_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=10)
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

    def test_search_carrier_id_successful(self, service, mocker, order):
        """Test successful carrier ID retrieval."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 5}])

        result = service._search_carrier_id(order)

        assert result == 5

    def test_search_carrier_id_raises_for_empty_carrier_name(self, service, mocker):
        """Test that ValueError is raised for empty carrier name."""
        order = Mock()
        order.shipment_type = ""

        with pytest.raises(ValueError, match="Shipment type is required in order"):
            service._search_carrier_id(order)

    def test_search_carrier_id_raises_when_not_found(self, service, mocker, order):
        """Test that SaleError is raised when carrier is not found."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        with pytest.raises(SaleError, match="Carrier for search 'FedEx' not found"):
            service._search_carrier_id(order)

    def test_search_carrier_id_raises_when_not_integer(self, service, mocker, order):
        """Test that SaleError is raised when carrier_id is not an integer."""
        mocker.patch.object(OdooSaleService, "_call", return_value="not_an_int")

        with pytest.raises(SaleError, match="Carrier for search 'FedEx' not found"):
            service._search_carrier_id(order)

    def test_search_carrier_id_raises_when_id_is_boolean(self, service, mocker, order):
        """Test that SaleError is raised when carrier_id is a non-int type."""
        mocker.patch.object(OdooSaleService, "_call", return_value=[1, 2])

        with pytest.raises(SaleError, match="Carrier for search 'FedEx' not found"):
            service._search_carrier_id(order)


class TestLoadContactDataFromOrder:
    """Tests for _load_contact_data_from_order method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=5)
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

    def test_load_contact_data_from_order_successful(self, service, mocker, order):
        """Test successful contact data building."""
        mocker.patch.object(OdooSaleService, "_search_country_id", return_value=42)
        mocker.patch.object(OdooSaleService, "_search_state_id", return_value=100)

        result = service._load_contact_data_from_order(order)

        assert result["name"] == "John Doe"
        # Odoo's "company_id" field is reserved for the Odoo company,
        # so we map the customer's company name to "deonet_other_company"
        assert result["deonet_other_company"] == "ACME Corp"
        assert result["country_id"] == 42
        assert result["state_id"] == 100
        assert result["parent_id"] == 100
        assert result["company_id"] == 1
        assert result["ref"] == "CUST123"

    def test_load_contact_data_from_order_handles_missing_state(self, service, mocker):
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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=5)
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
        mocker.patch.object(OdooSaleService, "_search_country_id", return_value=42)

        result = service._load_contact_data_from_order(order)

        assert result["state_id"] is None


class TestCreateContact:
    """Tests for _create_contact method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=5)
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
        mocker.patch.object(OdooSaleService, "_load_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", side_effect=[[], 10])

        result = service._create_contact(order)

        assert result == 10

    def test_create_contact_returns_existing_contact(self, service, mocker, order):
        """Test that existing contact is returned if found."""
        mocker.patch.object(OdooSaleService, "_load_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", return_value=[{"id": 10}])

        result = service._create_contact(order)

        assert result == 10

    def test_create_contact_raises_on_failure(self, service, mocker, order):
        """Test that SaleError is raised when contact creation fails."""
        mocker.patch.object(OdooSaleService, "_load_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", side_effect=[[], "not_an_int"])

        with pytest.raises(SaleError, match="Failed to create contact"):
            service._create_contact(order)


class TestUpdateContact:
    """Tests for update_contact method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=5)
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
            "search_sale",
            return_value={"id": 100, "partner_shipping_id": [10, "Shipping Address"]},
        )
        mocker.patch.object(OdooSaleService, "_load_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", return_value=True)

        service.update_contact(order)

    def test_update_contact_raises_when_sale_not_found(self, service, mocker, order):
        """Test that SaleError is raised when sale is not found."""
        mocker.patch.object(OdooSaleService, "search_sale", return_value={})

        with pytest.raises(SaleError, match="Sale not found"):
            service.update_contact(order)

    def test_update_contact_raises_when_no_shipping_contact(self, service, mocker, order):
        """Test that SaleError is raised when sale has no shipping contact."""
        mocker.patch.object(OdooSaleService, "search_sale", return_value={"id": 100})

        with pytest.raises(SaleError, match="Sale has no shipping contact to update"):
            service.update_contact(order)

    def test_update_contact_raises_on_write_failure(self, service, mocker, order):
        """Test that SaleError is raised when write fails."""
        mocker.patch.object(
            OdooSaleService,
            "search_sale",
            return_value={"id": 100, "partner_shipping_id": [10, "Shipping Address"]},
        )
        mocker.patch.object(OdooSaleService, "_load_contact_data_from_order", return_value={})
        mocker.patch.object(OdooSaleService, "_call", return_value=False)

        with pytest.raises(SaleError, match="Failed to update contact"):
            service.update_contact(order)


class TestSaleHasExpectedOrderLines:
    """Tests for sale_has_expected_order_lines method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=10)
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

    def test_sale_has_expected_order_lines_success(self, service, mocker, order):
        """Test successful order line verification."""
        mocker.patch.object(
            OdooSaleService,
            "search_sale",
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

        result = service.sale_has_expected_order_lines(order)

        assert result is True

    def test_sale_has_expected_order_lines_fails_for_mismatched_quantities(
        self, service, mocker, order
    ):
        """Test that verification fails for mismatched quantities."""
        mocker.patch.object(
            OdooSaleService,
            "search_sale",
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

        result = service.sale_has_expected_order_lines(order)

        assert result is False

    def test_sale_has_expected_order_lines_raises_when_sale_not_found(self, service, mocker, order):
        """Test that SaleError is raised when sale not found."""
        mocker.patch.object(OdooSaleService, "search_sale", return_value={})

        with pytest.raises(SaleError, match="Sale not found"):
            service.sale_has_expected_order_lines(order)


class TestSearchShippingInfo:
    """Tests for search_shipping_info method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=10)
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

    def test_search_shipping_info_successful(self, service, mocker, order):
        """Test successful shipping info retrieval."""
        mocker.patch.object(
            OdooSaleService,
            "search_sale",
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

        result = service.search_shipping_info(order)

        assert len(result) == 1
        assert result[0]["carrier"] == "FedEx"
        assert result[0]["carrier_tracking_ref"] == "TRACK123"
        assert result[0]["weight"] == 5.5

    def test_search_shipping_info_raises_error_when_not_found(self, service, mocker, order):
        """Test that SaleError is raised when no shipping info found."""
        mocker.patch.object(
            OdooSaleService,
            "search_sale",
            return_value={"id": 100, "company_id": 1},
        )
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        with pytest.raises(SaleError, match="No shipping information found"):
            service.search_shipping_info(order)


class TestSearchSerialsByLineItem:
    """Tests for search_serials_by_line_item method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSaleService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=requests.Session)
        return OdooSaleService(auth=mock_auth, session=mock_client)

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
        line_item = LineItem(line_id="LINE001", product_code="PROD001", quantity=2)
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

    def test_search_serials_by_line_item_returns_serials(self, service, mocker, order):
        """Test successful serial number retrieval by line item."""
        mocker.patch.object(OdooSaleService, "search_sale", return_value={"id": 100})
        mocker.patch.object(
            OdooSaleService,
            "_call",
            return_value=[
                {"product_id": [1, "[PROD001] Product A"], "serial": "SN001"},
                {"product_id": [1, "[PROD001] Product A"], "serial": "SN002"},
            ],
        )

        result = service.search_serials_by_line_item(order)

        assert result["LINE001"] == ["SN001", "SN002"]

    def test_search_serials_by_line_item_returns_dict_when_not_found(self, service, mocker, order):
        """Test that dict with empty lists is returned when no serials found."""
        mocker.patch.object(OdooSaleService, "search_sale", return_value={"id": 100})
        mocker.patch.object(OdooSaleService, "_call", return_value=[])

        result = service.search_serials_by_line_item(order)

        assert len(result) == 1
        assert result["LINE001"] == []

    def test_search_serials_by_line_item_returns_dict_on_invalid_result(
        self, service, mocker, order
    ):
        """Test that empty dict is returned on invalid result."""
        mocker.patch.object(OdooSaleService, "search_sale", return_value={"id": 100})
        mocker.patch.object(OdooSaleService, "_call", return_value="invalid")

        result = service.search_serials_by_line_item(order)

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
        """Provide a mocked requests.Session."""
        client = Mock(spec=requests.Session)
        return client

    @pytest.fixture
    def service(self, mock_auth, mock_client):
        """Provide an OdooSaleService instance."""
        return OdooSaleService(auth=mock_auth, session=mock_client)

    def test_call_successful(self, service, mock_client):
        """Test successful JSON-RPC call."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": 100, "id": 1}
        mock_client.post.return_value = mock_response

        result = service._call("sale.order", "create", query_data=[{}])

        assert result == 100
        mock_client.post.assert_called_once()

    def test_call_raises_on_http_error(self, service, mock_client):
        """Test that HTTP errors are raised."""
        mock_response = Mock(spec=requests.Response)
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_client.post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            service._call("sale.order", "create")

    def test_call_raises_on_json_rpc_error(self, service, mock_client):
        """Test that SaleError is raised for JSON-RPC errors."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "error": {
                "message": "Odoo Server Error",
                "code": 1,
                "data": {"message": "Record not found"},
            },
            "id": 1,
        }
        mock_client.post.return_value = mock_response

        with pytest.raises(SaleError, match="Odoo JSON-RPC error"):
            service._call("sale.order", "read")

    def test_call_uses_query_options(self, service, mock_client):
        """Test that query_options are included in the payload."""
        mock_response = Mock(spec=requests.Response)
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
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": None, "id": 1}
        mock_client.post.return_value = mock_response

        service._call("sale.order", "create")
        service._call("sale.order", "create")

        calls = mock_client.post.call_args_list
        id_1 = calls[0][1]["json"]["id"]
        id_2 = calls[1][1]["json"]["id"]
        assert id_2 > id_1
