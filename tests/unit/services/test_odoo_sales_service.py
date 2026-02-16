"""Unit tests for OdooSalesService."""

from datetime import date
from unittest.mock import Mock

import httpx
import pytest

from src.app.errors import SaleError
from src.app.odoo_auth import OdooAuth
from src.domain.line_item import LineItem
from src.domain.order import Order
from src.domain.ship_to import ShipTo
from src.services.odoo_sales_service import OdooSalesService


class TestOdooSalesServiceInstantiation:
    """Tests for OdooSalesService instantiation."""

    def test_instantiation_with_all_fields(self):
        """Test creating OdooSalesService with all required fields."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)

        service = OdooSalesService(auth=mock_auth, engine=mock_client)

        assert service.auth is mock_auth
        assert service.engine is mock_client

    def test_id_counter_initializes_correctly(self):
        """Test that _id_counter is initialized as an iterator."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)

        service = OdooSalesService(auth=mock_auth, engine=mock_client)

        assert next(service._id_counter) == 1
        assert next(service._id_counter) == 2


class TestCreateSale:
    """Tests for create_sale method."""

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
        """Provide a mocked httpx.Client."""
        return Mock(spec=httpx.Client)

    @pytest.fixture
    def service(self, mock_auth, mock_client):
        """Provide an OdooSalesService instance."""
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.product_id = "PROD001"
        line_item.quantity = 10

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(12345)
        order.set_ship_at(date(2027, 12, 25))
        return order

    def test_create_sale_successful(self, service, order, mocker):
        """Test successful sale creation."""
        # Mock the _execute_kw calls
        product_result = [{"id": 1, "name": "Product 1"}]
        sale_id_result = 100
        confirm_result = True

        # _execute_kw is called for: _build_odoo_product_line, create_sale, confirm_sale
        execute_kw_calls = [product_result, sale_id_result, confirm_result]
        mocker.patch.object(OdooSalesService, "_execute_kw", side_effect=execute_kw_calls)
        mocker.patch.object(OdooSalesService, "get_contact_id", return_value=0)
        mocker.patch.object(OdooSalesService, "create_contact", return_value=10)
        mocker.patch.object(OdooSalesService, "get_carrier_id", return_value=5)

        result = service.create_sale(order)

        assert result == 100

    def test_create_sale_uses_existing_contact(self, service, mocker, order):
        """Test that create_sale uses existing contact if found."""
        product_result = [{"id": 1, "name": "Product 1"}]
        sale_id_result = 100
        confirm_result = True

        # _execute_kw is called for: _build_odoo_product_line, create_sale, confirm_sale
        execute_kw_calls = [product_result, sale_id_result, confirm_result]
        mocker.patch.object(OdooSalesService, "_execute_kw", side_effect=execute_kw_calls)
        mocker.patch.object(OdooSalesService, "get_contact_id", return_value=10)
        mocker.patch.object(OdooSalesService, "get_carrier_id", return_value=5)

        result = service.create_sale(order)

        assert result == 100

    def test_create_sale_raises_on_failure(self, service, mocker, order):
        """Test that SaleError is raised when sale creation fails."""
        product_result = [{"id": 1, "name": "Product 1"}]

        # _execute_kw is called for: _build_odoo_product_line, create_sale
        # Return valid product, but invalid sale result
        mocker.patch.object(OdooSalesService, "get_contact_id", return_value=10)
        mocker.patch.object(OdooSalesService, "get_carrier_id", return_value=5)
        mocker.patch.object(
            OdooSalesService, "_execute_kw", side_effect=[product_result, "not_an_int"]
        )

        with pytest.raises(SaleError, match="Failed to create sale.order"):  # noqa: RUF043
            service.create_sale(order)

    def test_create_sale_raises_on_product_not_found(self, service, mocker, order):
        """Test that SaleError is raised when product is not found."""
        mocker.patch.object(OdooSalesService, "get_contact_id", return_value=10)
        mocker.patch.object(OdooSalesService, "get_carrier_id", return_value=5)
        mocker.patch.object(OdooSalesService, "_execute_kw", side_effect=[[], []])

        with pytest.raises(SaleError, match="Product ID PROD001 not found"):
            service.create_sale(order)


class TestConfirmSale:
    """Tests for confirm_sale method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    def test_confirm_sale_successful(self, service, mocker):
        """Test successful sale confirmation."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=True)

        service.confirm_sale(100)

    def test_confirm_sale_raises_on_failure(self, service, mocker):
        """Test that SaleError is raised when confirmation fails."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=False)

        with pytest.raises(SaleError, match="Failed to confirm sale.order id 100"):  # noqa: RUF043
            service.confirm_sale(100)


class TestGetSale:
    """Tests for get_sale method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(12345)
        return order

    def test_get_sale_returns_sale_when_found(self, service, mocker, order):
        """Test that get_sale returns sale data when found."""
        expected_sale = {"id": 100, "name": "SO-12345"}
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[expected_sale])

        result = service.get_sale(order)

        assert result == expected_sale

    def test_get_sale_returns_empty_dict_when_not_found(self, service, mocker, order):
        """Test that get_sale returns empty dict when not found."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[])

        result = service.get_sale(order)

        assert result == {}

    def test_get_sale_returns_empty_dict_on_invalid_result(self, service, mocker, order):
        """Test that get_sale returns empty dict on invalid result."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value="invalid")

        result = service.get_sale(order)

        assert result == {}


class TestGetCompletedSales:
    """Tests for get_completed_sales method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    def test_get_completed_sales_returns_ids(self, service, mocker):
        """Test that get_completed_sales returns list of IDs."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[100, 101, 102])

        result = service.get_completed_sales("Harman")

        assert result == [100, 101, 102]

    def test_get_completed_sales_returns_empty_list_when_not_found(self, service, mocker):
        """Test that get_completed_sales returns empty list when not found."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[])

        result = service.get_completed_sales("Harman")

        assert result == []

    def test_get_completed_sales_returns_empty_list_on_invalid_result(self, service, mocker):
        """Test that get_completed_sales returns empty list on invalid result."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[100, "invalid"])

        result = service.get_completed_sales("Harman")

        assert result == []


class TestBuildOdooProductLine:
    """Tests for _build_odoo_product_line method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def line_item(self, mocker):
        """Provide a LineItem instance."""
        item = mocker.Mock(spec=LineItem)
        item.product_id = "PROD001"
        item.quantity = 10
        return item

    def test_build_odoo_product_line_successful(self, service, mocker, line_item):
        """Test successful product line building."""
        product_data = [{"id": 1, "name": "Product 1"}]
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=product_data)

        result = service._build_odoo_product_line(line_item)

        assert result == {
            "product_id": 1,
            "name": "Product 1",
            "product_uom_qty": 10,
        }

    def test_build_odoo_product_line_raises_when_product_not_found(
        self, service, mocker, line_item
    ):
        """Test that SaleError is raised when product is not found."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[])

        with pytest.raises(SaleError, match="Product ID PROD001 not found"):
            service._build_odoo_product_line(line_item)

    def test_build_odoo_product_line_raises_on_invalid_result(self, service, mocker, line_item):
        """Test that SaleError is raised on invalid result."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value="invalid")

        with pytest.raises(SaleError, match="Product ID PROD001 not found"):
            service._build_odoo_product_line(line_item)


class TestGetCountryId:
    """Tests for get_country_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    def test_get_country_id_successful(self, service, mocker):
        """Test successful country ID retrieval."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[{"id": 42}])

        result = service.get_country_id("US")

        assert result == 42

    def test_get_country_id_handles_case_insensitive(self, service, mocker):
        """Test that country code is case insensitive."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[{"id": 42}])

        result = service.get_country_id("us")

        assert result == 42

    def test_get_country_id_handles_whitespace(self, service, mocker):
        """Test that whitespace is stripped from country code."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[{"id": 42}])

        result = service.get_country_id("  US  ")

        assert result == 42

    def test_get_country_id_raises_when_not_found(self, service, mocker):
        """Test that SaleError is raised when country is not found."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[])

        with pytest.raises(SaleError, match="Country code 'XX' not found"):
            service.get_country_id("XX")

    def test_get_country_id_raises_on_invalid_result(self, service, mocker):
        """Test that SaleError is raised on invalid result."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value="invalid")

        with pytest.raises(SaleError, match="Country code 'US' not found"):
            service.get_country_id("US")


class TestGetStateId:
    """Tests for get_state_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    def test_get_state_id_successful(self, service, mocker):
        """Test successful state ID retrieval."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[{"id": 123}])

        result = service.get_state_id(42, "California")

        assert result == 123

    def test_get_state_id_returns_zero_for_empty_state(self, service, mocker):
        """Test that 0 is returned for empty state."""
        spy = mocker.spy(OdooSalesService, "_execute_kw")

        result = service.get_state_id(42, "")

        assert result == 0
        spy.assert_not_called()

    def test_get_state_id_returns_zero_for_whitespace_state(self, service, mocker):
        """Test that 0 is returned for whitespace-only state."""
        spy = mocker.spy(OdooSalesService, "_execute_kw")

        result = service.get_state_id(42, "   ")

        assert result == 0
        spy.assert_not_called()

    def test_get_state_id_returns_zero_when_not_found(self, service, mocker):
        """Test that 0 is returned when state is not found."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[])

        result = service.get_state_id(42, "NonExistent")

        assert result == 0

    def test_get_state_id_strips_whitespace(self, service, mocker):
        """Test that whitespace is stripped from state name."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[{"id": 123}])

        result = service.get_state_id(42, "  California  ")

        assert result == 123


class TestGetCarrierId:
    """Tests for get_carrier_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    def test_get_carrier_id_successful(self, service, mocker):
        """Test successful carrier ID retrieval."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[{"id": 5}])

        result = service.get_carrier_id(1, "FedEx")

        assert result == 5

    def test_get_carrier_id_raises_for_empty_carrier_name(self, service):
        """Test that ValueError is raised for empty carrier name."""
        with pytest.raises(ValueError, match="Carrier name is empty"):
            service.get_carrier_id(1, "")

    def test_get_carrier_id_raises_for_whitespace_carrier_name(self, service):
        """Test that ValueError is raised for whitespace-only carrier name."""
        with pytest.raises(ValueError, match="Carrier name is empty"):
            service.get_carrier_id(1, "   ")

    def test_get_carrier_id_raises_when_not_found(self, service, mocker):
        """Test that SaleError is raised when carrier is not found."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[])

        with pytest.raises(SaleError, match="Carrier 'FedEx' not found"):
            service.get_carrier_id(1, "FedEx")

    def test_get_carrier_id_raises_on_invalid_result(self, service, mocker):
        """Test that SaleError is raised on invalid result."""
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value="invalid")

        with pytest.raises(SaleError, match="Carrier 'FedEx' not found"):
            service.get_carrier_id(1, "FedEx")


class TestBuildContactData:
    """Tests for _build_contact_data method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order with ShipTo."""
        ship_to = mocker.Mock(spec=ShipTo)
        ship_to.remote_customer_id = "CUST123"
        ship_to.contact_name = "John Doe"
        ship_to.company_name = "ACME Corp"
        ship_to.country_code = "US"
        ship_to.state = "California"
        ship_to.street1 = "123 Main St"
        ship_to.street2 = "Apt 4"
        ship_to.city = "San Francisco"
        ship_to.postal_code = "94102"
        ship_to.phone = "555-1234"
        ship_to.email = "john@acme.com"

        line_item = mocker.Mock(spec=LineItem)
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        return order

    def test_build_contact_data_successful(self, service, mocker, order):
        """Test successful contact data building."""
        mocker.patch.object(OdooSalesService, "get_country_id", return_value=42)
        mocker.patch.object(OdooSalesService, "get_state_id", return_value=100)

        result = service._build_contact_data(order)

        assert result["name"] == "John Doe"
        assert result["company_name"] == "ACME Corp"
        assert result["country_id"] == 42
        assert result["state_id"] == 100
        assert result["parent_id"] == 100
        assert result["company_id"] == 1

    def test_build_contact_data_handles_missing_street2(self, service, mocker, order):
        """Test that missing street2 is handled correctly."""
        order.ship_to.street2 = None
        mocker.patch.object(OdooSalesService, "get_country_id", return_value=42)
        mocker.patch.object(OdooSalesService, "get_state_id", return_value=100)

        result = service._build_contact_data(order)

        assert result["street2"] is None

    def test_build_contact_data_handles_missing_company_name(self, service, mocker, order):
        """Test that missing company name is handled correctly."""
        order.ship_to.company_name = None
        mocker.patch.object(OdooSalesService, "get_country_id", return_value=42)
        mocker.patch.object(OdooSalesService, "get_state_id", return_value=100)

        result = service._build_contact_data(order)

        assert result["company_name"] is None

    def test_build_contact_data_handles_empty_state(self, service, mocker, order):
        """Test that empty state is handled correctly."""
        order.ship_to.state = ""
        mocker.patch.object(OdooSalesService, "get_country_id", return_value=42)

        result = service._build_contact_data(order)

        assert result["state_id"] is None


class TestGetContactId:
    """Tests for get_contact_id method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        ship_to.remote_customer_id = "CUST123"
        ship_to.contact_name = "John Doe"
        ship_to.company_name = "ACME Corp"
        ship_to.country_code = "US"
        ship_to.state = "California"
        ship_to.street1 = "123 Main St"
        ship_to.street2 = None
        ship_to.city = "San Francisco"
        ship_to.postal_code = "94102"
        ship_to.phone = "555-1234"
        ship_to.email = "john@acme.com"

        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_get_contact_id_returns_id_when_found(self, service, mocker, order):
        """Test that contact ID is returned when found."""
        mocker.patch.object(OdooSalesService, "_build_contact_data", return_value={})
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[{"id": 10}])

        result = service.get_contact_id(order)

        assert result == 10

    def test_get_contact_id_returns_zero_when_not_found(self, service, mocker, order):
        """Test that 0 is returned when contact is not found."""
        mocker.patch.object(OdooSalesService, "_build_contact_data", return_value={})
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=[])

        result = service.get_contact_id(order)

        assert result == 0

    def test_get_contact_id_returns_zero_on_invalid_result(self, service, mocker, order):
        """Test that 0 is returned on invalid result."""
        mocker.patch.object(OdooSalesService, "_build_contact_data", return_value={})
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value="invalid")

        result = service.get_contact_id(order)

        assert result == 0


class TestCreateContact:
    """Tests for create_contact method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        ship_to.remote_customer_id = "CUST123"
        ship_to.contact_name = "John Doe"
        ship_to.company_name = "ACME Corp"
        ship_to.country_code = "US"
        ship_to.state = "California"
        ship_to.street1 = "123 Main St"
        ship_to.street2 = None
        ship_to.city = "San Francisco"
        ship_to.postal_code = "94102"
        ship_to.phone = "555-1234"
        ship_to.email = "john@acme.com"

        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_create_contact_successful(self, service, mocker, order):
        """Test successful contact creation."""
        mocker.patch.object(OdooSalesService, "_build_contact_data", return_value={})
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=10)

        result = service.create_contact(order)

        assert result == 10

    def test_create_contact_raises_on_failure(self, service, mocker, order):
        """Test that SaleError is raised when contact creation fails."""
        mocker.patch.object(OdooSalesService, "_build_contact_data", return_value={})
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value="not_an_int")

        with pytest.raises(SaleError, match="Failed to create contact"):
            service.create_contact(order)


class TestUpdateContact:
    """Tests for update_contact method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        ship_to.remote_customer_id = "CUST123"
        ship_to.contact_name = "John Doe"
        ship_to.company_name = "ACME Corp"
        ship_to.country_code = "US"
        ship_to.state = "California"
        ship_to.street1 = "123 Main St"
        ship_to.street2 = None
        ship_to.city = "San Francisco"
        ship_to.postal_code = "94102"
        ship_to.phone = "555-1234"
        ship_to.email = "john@acme.com"

        line_item = mocker.Mock(spec=LineItem)
        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_update_contact_successful(self, service, mocker, order):
        """Test successful contact update."""
        mocker.patch.object(OdooSalesService, "get_contact_id", return_value=10)
        mocker.patch.object(OdooSalesService, "_build_contact_data", return_value={})
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=True)

        result = service.update_contact(order)

        assert result is True

    def test_update_contact_raises_when_contact_not_found(self, service, mocker, order):
        """Test that SaleError is raised when contact is not found."""
        mocker.patch.object(OdooSalesService, "get_contact_id", return_value=0)

        with pytest.raises(SaleError, match="Could not find contact"):
            service.update_contact(order)

    def test_update_contact_raises_on_write_failure(self, service, mocker, order):
        """Test that SaleError is raised when write fails."""
        mocker.patch.object(OdooSalesService, "get_contact_id", return_value=10)
        mocker.patch.object(OdooSalesService, "_build_contact_data", return_value={})
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=False)

        with pytest.raises(SaleError, match="Failed to update contact"):
            service.update_contact(order)


class TestVerifySaleQuantities:
    """Tests for verify_sale_quantities method."""

    @pytest.fixture
    def service(self):
        """Provide an OdooSalesService instance."""
        mock_auth = Mock(spec=OdooAuth)
        mock_client = Mock(spec=httpx.Client)
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.product_id = "PROD001"
        line_item.quantity = 10

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        return order

    @pytest.fixture
    def sale(self):
        """Provide a sale dict."""
        return {"id": 100, "company_id": 1}

    def test_verify_sale_quantities_success(self, service, mocker, order, sale):
        """Test successful quantity verification."""
        sale_line_data = [
            {
                "id": 1,
                "product_id": [1, "[PROD001]"],
                "product_uom_qty": 10,
            }
        ]
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=sale_line_data)

        result = service.verify_sale_quantities(order, sale)

        assert result is True

    def test_verify_sale_quantities_fails_for_mismatched_quantities(
        self, service, mocker, order, sale
    ):
        """Test that verification fails for mismatched quantities."""
        sale_line_data = [
            {
                "id": 1,
                "product_id": [1, "[PROD001]"],
                "product_uom_qty": 20,
            }
        ]
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=sale_line_data)

        result = service.verify_sale_quantities(order, sale)

        assert result is False

    def test_verify_sale_quantities_fails_for_mismatched_product_id(
        self, service, mocker, order, sale
    ):
        """Test that verification fails for mismatched product ID."""
        sale_line_data = [
            {
                "id": 1,
                "product_id": [1, "[PROD002]"],
                "product_uom_qty": 10,
            }
        ]
        mocker.patch.object(OdooSalesService, "_execute_kw", return_value=sale_line_data)

        result = service.verify_sale_quantities(order, sale)

        assert result is False

    def test_verify_sale_quantities_raises_for_invalid_sale(self, service, mocker, order):
        """Test that SaleError is raised for invalid sale data."""
        with pytest.raises(SaleError, match="Invalid sale data"):
            service.verify_sale_quantities(order, None)

    def test_verify_sale_quantities_raises_for_sale_without_id(self, service, mocker, order):
        """Test that SaleError is raised for sale without ID."""
        with pytest.raises(SaleError, match="Invalid sale data"):
            service.verify_sale_quantities(order, {})


class TestExecuteKw:
    """Tests for _execute_kw method."""

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
        """Provide a mocked httpx.Client."""
        return Mock(spec=httpx.Client)

    @pytest.fixture
    def service(self, mock_auth, mock_client):
        """Provide an OdooSalesService instance."""
        return OdooSalesService(auth=mock_auth, engine=mock_client)

    def test_execute_kw_successful(self, service, mock_client):
        """Test successful JSON-RPC execution."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": 100, "id": 1}
        mock_client.post.return_value = mock_response

        result = service._execute_kw("sale.order", "create", query_data=[{}])

        assert result == 100
        mock_client.post.assert_called_once()

    def test_execute_kw_raises_on_http_error(self, service, mock_client):
        """Test that HTTP errors are raised."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=Mock(), response=mock_response
        )
        mock_client.post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            service._execute_kw("sale.order", "create")

    def test_execute_kw_raises_on_json_rpc_error(self, service, mock_client):
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
            service._execute_kw("sale.order", "read")

    def test_execute_kw_uses_query_options(self, service, mock_client):
        """Test that query_options are included in the payload."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": [], "id": 1}
        mock_client.post.return_value = mock_response

        service._execute_kw(
            "sale.order",
            "search_read",
            query_data=[[["id", "=", 100]]],
            query_options={"limit": 1},
        )

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["params"]["args"][6] == {"limit": 1}

    def test_execute_kw_increments_id_counter(self, service, mock_client):
        """Test that ID counter is incremented for each call."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"jsonrpc": "2.0", "result": None, "id": 1}
        mock_client.post.return_value = mock_response

        service._execute_kw("sale.order", "create")
        service._execute_kw("sale.order", "create")

        calls = mock_client.post.call_args_list
        id_1 = calls[0][1]["json"]["id"]
        id_2 = calls[1][1]["json"]["id"]
        assert id_2 > id_1
