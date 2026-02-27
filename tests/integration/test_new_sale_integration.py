"""Integration tests for NewSaleUseCase."""

from io import BytesIO
from unittest.mock import Mock
from zipfile import ZipFile

import httpx
import pytest

from src.app.new_sale_use_case import NewSaleUseCase
from src.app.registry import Registry
from src.services.odoo_sale_service import OdooSaleService
from src.services.spectrum_artwork_service import SpectrumArtworkService


class TestNewSaleUseCaseIntegration:
    """Integration tests for NewSaleUseCase with multiple services."""

    @pytest.fixture
    def order_service_mock(self, sample_order):
        """Provide a mock order service that returns a sample order."""
        service = Mock()
        service.read_orders.return_value = [sample_order]
        service.persist_order = Mock()
        return service

    @pytest.fixture
    def order_services(self, order_service_mock):
        """Provide a registry with a mock order service."""
        registry = Registry()
        registry.register("TestOrderService", order_service_mock)
        return registry

    @pytest.fixture
    def artwork_services(self):
        """Provide an empty artwork services registry."""
        return Registry()

    def test_new_sale_creation_with_mock_http(
        self,
        httpx_mock,
        odoo_auth,
        temp_dir,
        order_services,
        artwork_services,
        error_queue,
        sample_order,
    ):
        """Test creating a new sale checks if it exists in Odoo."""
        # This test verifies the integration flow without full sale creation

        # Mock Odoo search for existing sale (not found)
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8069/jsonrpc",
            json={"jsonrpc": "2.0", "id": 1, "result": []},
        )

        with httpx.Client(base_url="http://localhost:8069") as odoo_client:
            sale_service = OdooSaleService(auth=odoo_auth, engine=odoo_client)

            # Just verify that is_sale_created works correctly
            result = sale_service.is_sale_created(sample_order)

            assert result is False

    def test_new_sale_with_artwork_service(
        self,
        httpx_mock,
        temp_dir,
        sample_order,
    ):
        """Test getting artwork from Spectrum service."""
        # Set the sale_id on the sample order
        sample_order.set_sale_id(100)

        # Mock order lookup
        httpx_mock.add_response(
            method="GET",
            url="https://spectrum.example.com/api/order/order-number/ORDER123/",
            json={
                "clientHandle": "test_client",
                "line_items": [
                    {
                        "recipeSetId": "RECIPE123",
                        "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                    }
                ],
            },
        )

        # Mock design download (zip file)
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zf:
            zf.writestr("design.pdf", b"design content")
        zip_buffer.seek(0)

        httpx_mock.add_response(
            method="GET",
            url="https://spectrum.example.com/api/webtoprint/RECIPE123/",
            content=zip_buffer.getvalue(),
        )

        # Mock placement PDF
        httpx_mock.add_response(
            method="GET",
            url="https://spectrum.example.com/test_client/specification/RECIPE123/pdf/",
            content=b"placement pdf content",
        )

        with httpx.Client(base_url="https://spectrum.example.com") as spectrum_client:
            spectrum_client.headers["SPECTRUM_API_TOKEN"] = "test_token"
            artwork_service = SpectrumArtworkService(
                engine=spectrum_client,
                digitals_dir=temp_dir,
            )

            # Get artwork
            file_paths = artwork_service.get_artwork(sample_order)

            # Verify artwork was downloaded
            assert len(file_paths) == 2  # design + placement
            assert (temp_dir / "S00100_design.pdf").exists()
            assert (temp_dir / "S00100_RECIPE123_placement.pdf").exists()

    def test_new_sale_handles_missing_sale(
        self,
        httpx_mock,
        odoo_auth,
        temp_dir,
        error_queue,
    ):
        """Test that missing orders are properly handled."""
        # Setup empty order service
        order_service = Mock()
        order_service.read_orders.return_value = []

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        artwork_services = Registry()

        with httpx.Client(base_url="http://localhost:8069") as odoo_client:
            sale_service = OdooSaleService(auth=odoo_auth, engine=odoo_client)

            use_case = NewSaleUseCase(
                order_services=order_services,
                artwork_services=artwork_services,
                sale_service=sale_service,
                error_queue=error_queue,
                open_orders_dir=temp_dir,
            )

            # Execute the use case with no orders
            use_case.execute()

            # Verify no errors were queued
            error_queue.put.assert_not_called()

    def test_new_sale_error_handling(
        self,
        httpx_mock,
        odoo_auth,
        temp_dir,
        error_queue,
        sample_order,
    ):
        """Test that errors during sale creation are properly queued."""
        # Setup order service that returns a valid order but sale creation fails
        order_service = Mock()
        order_service.read_orders.return_value = [sample_order]
        order_service.persist_order = Mock()

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        artwork_services = Registry()

        # Mock Odoo calls that will fail
        httpx_mock.add_response(
            method="POST",
            url="http://localhost:8069/jsonrpc",
            status_code=500,  # Server error
        )

        with httpx.Client(base_url="http://localhost:8069") as odoo_client:
            sale_service = OdooSaleService(auth=odoo_auth, engine=odoo_client)

            use_case = NewSaleUseCase(
                order_services=order_services,
                artwork_services=artwork_services,
                sale_service=sale_service,
                error_queue=error_queue,
                open_orders_dir=temp_dir,
            )

            # Execute the use case - should handle the error gracefully
            use_case.execute()

            # Verify error was queued
            error_queue.put.assert_called()
