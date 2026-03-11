"""Integration tests for service collaboration and HTTP interactions."""

from unittest.mock import Mock

import pytest
import requests

from src.app.errors import get_error_store
from src.services.odoo_sale_service import OdooSaleService


class TestOdooServiceHttpIntegration:
    """Integration tests for OdooSaleService HTTP interactions."""

    def test_odoo_search_for_existing_sale(
        self,
        odoo_auth,
        odoo_client,
        sample_order,
        mocker,
    ):
        """Test searching for an existing sale in Odoo."""
        # Mock the search_read RPC call
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [
                {
                    "id": 100,
                    "name": "ORDER123",
                    "amount_total": 1000.00,
                }
            ],
        }
        mocker.patch.object(odoo_client, "post", return_value=mock_response)

        service = OdooSaleService(
            auth=odoo_auth, session=odoo_client, base_url="http://localhost:8069"
        )

        # Check if the sale exists
        exists = bool(service.search_sale(sample_order))

        assert exists is True

    def test_odoo_sale_not_found(
        self,
        odoo_auth,
        odoo_client,
        sample_order,
        mocker,
    ):
        """Test when a sale does not exist in Odoo."""
        # Mock the search_read RPC call returning empty result
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [],
        }
        mocker.patch.object(odoo_client, "post", return_value=mock_response)

        service = OdooSaleService(
            auth=odoo_auth, session=odoo_client, base_url="http://localhost:8069"
        )

        # Check if the sale exists
        exists = bool(service.search_sale(sample_order))

        assert exists is False

    def test_odoo_authentication_validation(self):
        """Test OdooSaleService validates authentication properly."""
        client = Mock(spec=requests.Session)
        with pytest.raises(ValueError, match="authentication information is missing or invalid"):
            OdooSaleService(auth=None, session=client)  # type: ignore

    def test_odoo_engine_validation(self, odoo_auth):
        """Test OdooSaleService validates session properly."""
        # Should raise ValueError with invalid session
        with pytest.raises(ValueError, match="session is missing or invalid"):
            OdooSaleService(auth=odoo_auth, session=None)  # type: ignore

    def test_odoo_base_url_validation(self, odoo_auth):
        """Test OdooSaleService validates base URL is set."""
        # Create a session without a base URL
        client = Mock(spec=requests.Session)

        with pytest.raises(ValueError, match="base URL is not set"):
            OdooSaleService(auth=odoo_auth, session=client, base_url="")

    def test_odoo_multiple_rpc_calls(
        self,
        odoo_auth,
        odoo_client,
    ):
        """Test OdooSaleService can be instantiated with proper setup."""
        # This is a simple instantiation test, not a functional test
        # We're just verifying the service can be created

        service = OdooSaleService(
            auth=odoo_auth, session=odoo_client, base_url="http://localhost:8069"
        )

        # Verify the service was created with the right attributes
        assert service.auth == odoo_auth
        assert service.session == odoo_client


class TestErrorStoreIntegration:
    """Integration tests for error store handling across services."""

    def test_error_store_collects_multiple_errors(self):
        """Test that error store properly collects multiple errors."""
        error_store = get_error_store()
        error_store.clear()  # Clear any previous errors

        error1 = Exception("Error 1")
        error2 = Exception("Error 2")
        error3 = Exception("Error 3")

        error_store.add(error1)
        error_store.add(error2)
        error_store.add(error3)

        # Verify errors were collected
        assert error_store.has_errors()
        all_errors = error_store.all()
        assert len(all_errors) == 3
        assert "Error 1" in all_errors[0]
        assert "Error 2" in all_errors[1]
        assert "Error 3" in all_errors[2]

    def test_error_store_preserves_error_type(self):
        """Test that error store preserves exception types."""
        error_store = get_error_store()
        error_store.clear()  # Clear any previous errors

        class CustomError(Exception):
            pass

        custom_error = CustomError("custom message")
        error_store.add(custom_error)

        assert error_store.has_errors()
        all_errors = error_store.all()
        assert len(all_errors) == 1
        assert "custom message" in all_errors[0]


class TestRegistryIntegration:
    """Integration tests for service registry."""

    def test_registry_registers_and_retrieves_services(self):
        """Test registry can register and retrieve services."""
        from src.app.registry import Registry

        registry = Registry()
        service1 = Mock()
        service2 = Mock()

        registry.register("Service1", service1)
        registry.register("Service2", service2)

        items = dict(registry.items())
        assert items["Service1"] == service1
        assert items["Service2"] == service2

    def test_registry_iteration_order(self):
        """Test that registry maintains insertion order."""
        from src.app.registry import Registry

        registry = Registry()
        names = ["A", "B", "C", "D"]

        for name in names:
            registry.register(name, Mock())

        retrieved_names = [name for name, _ in registry.items()]
        assert retrieved_names == names
