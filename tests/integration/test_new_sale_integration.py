"""Integration tests for NewSaleUseCase."""

from io import BytesIO
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
import requests

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
        odoo_auth,
        odoo_client,
        temp_dir,
        order_services,
        artwork_services,
        error_store,
        sample_order,
        mocker,
    ):
        """Test creating a new sale checks if it exists in Odoo."""
        # This test verifies the integration flow without full sale creation

        # Mock Odoo search for existing sale (not found)
        mock_response = Mock()
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": []}
        mocker.patch.object(odoo_client, "post", return_value=mock_response)

        sale_service = OdooSaleService(
            auth=odoo_auth, session=odoo_client, base_url="http://localhost:8069"
        )

        # Just verify that is_sale_created works correctly
        result = sale_service.search_sale(sample_order)

        assert bool(result) is False

    def test_new_sale_with_artwork_service(
        self,
        temp_dir,
        sample_order,
    ):
        """Test getting artwork from Spectrum service."""
        # Set the sale_id and sale_name on the sample order
        sample_order.set_sale_id(100)
        sample_order.set_sale_name("SO-12345")

        # Create a mock requests.Session
        mock_session = Mock(spec=requests.Session)

        # Create a mock response for order lookup
        order_response = Mock(spec=requests.Response)
        order_response.json.return_value = {
            "clientHandle": "test_client",
            "lineItems": [
                {
                    "id": 1,
                    "recipeSetId": "RECIPE123",
                    "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                }
            ],
        }

        # Create a mock response for design download (zip file)
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zf:
            zf.writestr("design.pdf", b"design content")
        zip_buffer.seek(0)

        design_response = Mock(spec=requests.Response)
        design_response.content = zip_buffer.getvalue()

        # Create a mock response for placement PDF
        placement_response = Mock(spec=requests.Response)
        placement_response.content = b"placement pdf content"

        # Setup side_effect to return different responses based on URL
        def mock_get(url=None, **kwargs):
            if "webtoprint" in str(url):
                return design_response
            elif "pdf" in str(url):
                return placement_response
            else:
                return order_response

        mock_session.get.side_effect = mock_get
        mock_session.headers = {}

        artwork_service = SpectrumArtworkService(
            session=mock_session,
            base_url="https://spectrum.example.com",
            digitals_dir=temp_dir,
        )

        # Get artwork
        file_paths = artwork_service.get_artwork(sample_order)

        # Verify artwork was downloaded
        assert len(file_paths) == 2  # design + placement
        assert (temp_dir / "SO-12345_design.pdf").exists()
        assert (temp_dir / "SO-12345_RECIPE123_placement.pdf").exists()

    def test_new_sale_handles_missing_sale(
        self,
        odoo_auth,
        odoo_client,
        temp_dir,
        error_store,
        mocker,
    ):
        """Test that missing orders are properly handled."""
        # Setup empty order service
        order_service = Mock()
        order_service.read_orders.return_value = []

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        artwork_services = Registry()

        sale_service = OdooSaleService(
            auth=odoo_auth, session=odoo_client, base_url="http://localhost:8069"
        )

        use_case = NewSaleUseCase(
            order_services=order_services,
            artwork_services=artwork_services,
            sale_service=sale_service,
            open_orders_dir=temp_dir,
        )

        # Execute the use case with no orders
        use_case.execute()

        # Verify no errors were stored
        error_store.add.assert_not_called()

    def test_new_sale_error_handling(
        self,
        odoo_auth,
        odoo_client,
        temp_dir,
        error_store,
        sample_order,
        mocker,
    ):
        """Test that errors during sale creation are properly stored."""
        # Setup order service that returns a valid order but sale creation fails
        order_service = Mock()
        order_service.read_orders.return_value = [sample_order]
        order_service.persist_order = Mock()

        order_services = Registry()
        order_services.register("TestOrderService", order_service)

        artwork_services = Registry()

        # Mock Odoo calls that will fail with HTTPError
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")
        mocker.patch.object(odoo_client, "post", return_value=mock_response)

        sale_service = OdooSaleService(
            auth=odoo_auth, session=odoo_client, base_url="http://localhost:8069"
        )

        use_case = NewSaleUseCase(
            order_services=order_services,
            artwork_services=artwork_services,
            sale_service=sale_service,
            open_orders_dir=temp_dir,
        )

        # Execute the use case - should handle the error gracefully
        use_case.execute()

        # Verify error was stored
        error_store.add.assert_called()
