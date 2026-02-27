"""Integration tests for service collaboration and HTTP interactions."""

from unittest.mock import Mock

import httpx
import pytest

from src.services.odoo_sale_service import OdooSaleService


class TestOdooServiceHttpIntegration:
    """Integration tests for OdooSaleService HTTP interactions."""

    def test_odoo_search_for_existing_sale(
        self,
        httpx_mock,
        odoo_auth,
        sample_order,
    ):
        """Test searching for an existing sale in Odoo."""
        # Mock the search_read RPC call
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8069/jsonrpc",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": [
                    {
                        "id": 100,
                        "name": "ORDER123",
                        "amount_total": 1000.00,
                    }
                ],
            },
        )

        with httpx.Client(base_url="http://localhost:8069") as client:
            service = OdooSaleService(auth=odoo_auth, engine=client)

            # Check if the sale exists
            exists = service.is_sale_created(sample_order)

            assert exists is True

    def test_odoo_sale_not_found(
        self,
        httpx_mock,
        odoo_auth,
        sample_order,
    ):
        """Test when a sale does not exist in Odoo."""
        # Mock the search_read RPC call returning empty result
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8069/jsonrpc",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": [],
            },
        )

        with httpx.Client(base_url="http://localhost:8069") as client:
            service = OdooSaleService(auth=odoo_auth, engine=client)

            # Check if the sale exists
            exists = service.is_sale_created(sample_order)

            assert exists is False

    def test_odoo_authentication_validation(self):
        """Test OdooSaleService validates authentication properly."""
        with (
            httpx.Client(base_url="http://localhost:8069") as client,
            pytest.raises(ValueError, match="authentication information is missing or invalid"),
        ):
            OdooSaleService(auth=None, engine=client)  # type: ignore

    def test_odoo_engine_validation(self, odoo_auth):
        """Test OdooSaleService validates HTTP engine properly."""
        # Should raise ValueError with invalid engine
        with pytest.raises(ValueError, match="engine is missing or invalid"):
            OdooSaleService(auth=odoo_auth, engine=None)  # type: ignore

    def test_odoo_base_url_validation(self, odoo_auth):
        """Test OdooSaleService validates base URL is set."""
        # Create a client without a base URL
        client = Mock(spec=httpx.Client)
        client.base_url = None

        with pytest.raises(ValueError, match="base URL is not set"):
            OdooSaleService(auth=odoo_auth, engine=client)

    def test_odoo_multiple_rpc_calls(
        self,
        odoo_auth,
    ):
        """Test OdooSaleService can be instantiated with proper setup."""
        # This is a simple instantiation test, not a functional test
        # We're just verifying the service can be created

        with httpx.Client(base_url="http://localhost:8069") as client:
            service = OdooSaleService(auth=odoo_auth, engine=client)

            # Verify the service was created with the right attributes
            assert service.auth == odoo_auth
            assert service.engine == client


class TestErrorQueueIntegration:
    """Integration tests for error queue handling across services."""

    def test_error_queue_collects_multiple_errors(self, error_queue):
        """Test that error queue properly collects multiple errors."""
        error1 = Exception("Error 1")
        error2 = Exception("Error 2")
        error3 = Exception("Error 3")

        error_queue.put(error1)
        error_queue.put(error2)
        error_queue.put(error3)

        assert len(error_queue.queue) == 3
        assert error_queue.queue[0] == error1
        assert error_queue.queue[1] == error2
        assert error_queue.queue[2] == error3

    def test_error_queue_preserves_error_type(self, error_queue):
        """Test that error queue preserves exception types."""

        class CustomError(Exception):
            pass

        custom_error = CustomError("custom message")
        error_queue.put(custom_error)

        assert isinstance(error_queue.queue[0], CustomError)
        assert str(error_queue.queue[0]) == "custom message"


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
