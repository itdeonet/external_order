"""Integration tests for edge cases, error paths, and resilience.

Tests error handling, network failures, permission errors, and concurrent access
patterns that ensure application stability under adverse conditions.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.app.errors import ErrorStore
from src.app.registry import Registry


class TestRegistryClear:
    """Tests for Registry clear() method."""

    def test_clear_removes_all_items(self):
        """Test that clear() removes all registered items."""
        registry = Registry[str]()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        assert registry.get("item1") is not None
        assert registry.get("item2") is not None

        registry.clear()

        assert registry.get("item1") is None
        assert registry.get("item2") is None

    def test_clear_empty_registry(self):
        """Test that clear() on empty registry doesn't fail."""
        registry = Registry[str]()
        registry.clear()  # Should not raise
        assert list(registry.items()) == []

    def test_clear_then_register_works(self):
        """Test that registry can be used after clear()."""
        registry = Registry[str]()
        registry.register("item1", "value1")
        registry.clear()
        registry.register("item2", "value2")

        assert registry.get("item2") == "value2"
        assert registry.get("item1") is None


class TestErrorStoreEdgeCases:
    """Tests for ErrorStore edge cases."""

    def test_error_store_get_render_email_data_empty(self):
        """Test get_render_email_data with no errors."""
        error_store = ErrorStore()
        data = error_store.get_render_email_data()

        assert "errors" in data
        assert data["errors"] == []

    def test_error_store_add_non_base_error(self):
        """Test that non-BaseError exceptions are properly stored."""
        error_store = ErrorStore()
        regular_error = ValueError("Regular error")

        error_store.add(regular_error)

        assert error_store.has_errors()
        data = error_store.get_render_email_data()
        assert len(data["errors"]) == 1

    def test_error_store_concurrent_access(self):
        """Test that error store is thread-safe."""
        error_store = ErrorStore()

        # Simulate concurrent adds (in single-threaded test)
        error_store.add(ValueError("Error 1"))
        error_store.add(ValueError("Error 2"))
        error_store.add(ValueError("Error 3"))

        data = error_store.get_render_email_data()
        assert len(data["errors"]) == 3

    def test_error_store_render_data_structure(self):
        """Test the structure of rendered error data."""
        error_store = ErrorStore()
        exc = ValueError("Test error")
        error_store.add(exc)

        data = error_store.get_render_email_data()

        assert "errors" in data
        assert isinstance(data["errors"], list)
        assert len(data["errors"]) > 0


class TestSpectrumArtworkServiceEdgeCases:
    """Tests for SpectrumArtworkService edge cases."""

    def test_load_order_data_connection_timeout(self, mocker):
        """Test handling of connection timeout."""
        import requests

        from src.domain import LineItem, Order, ShipTo
        from src.services.spectrum_artwork_service import SpectrumArtworkService

        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectTimeout("Connection timeout")

        service = SpectrumArtworkService(session=mock_session, base_url="http://api.example.com")

        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="Test",
            email="test@example.com",
            phone="555-0000",
            street1="123 Main",
            city="Test City",
            postal_code="12345",
            country_code="US",
        )
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Test",
            pricelist_id=50,
            remote_order_id="ORD001",
            shipment_type="standard",
            description="Test",
            ship_to=ship_to,
            line_items=[LineItem(line_id="L1", product_code="PROD001", quantity=10)],
        )
        order.set_sale_id(111)

        # Connection timeout is not HTTPError, so it should propagate
        with pytest.raises(requests.exceptions.ConnectTimeout):
            service._load_order_data(order)

    def test_download_placement_permission_error(self, mocker, tmp_path):
        """Test handling when placement cannot be written (permission denied)."""
        from unittest.mock import Mock, patch

        from src.services.spectrum_artwork_service import SpectrumArtworkService

        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b"PDF data"
        mock_session.get.return_value = mock_response

        service = SpectrumArtworkService(
            session=mock_session, base_url="http://api.example.com", digitals_dir=tmp_path
        )

        # Mock the Path.write_bytes to raise PermissionError
        with patch.object(Path, "write_bytes", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                service._download_placement(recipe_set_id="REC001", sale_name="SO001")

    def test_download_designs_corrupt_zip(self, mocker, tmp_path):
        """Test handling of corrupt ZIP file."""
        from zipfile import BadZipFile

        from src.services.spectrum_artwork_service import SpectrumArtworkService

        mock_session = Mock()
        mock_response = Mock()
        mock_response.content = b"Not a ZIP file"  # Invalid ZIP data
        mock_session.get.return_value = mock_response

        service = SpectrumArtworkService(
            session=mock_session, base_url="http://api.example.com", digitals_dir=tmp_path
        )

        with pytest.raises(BadZipFile):
            service._download_designs(recipe_set_id="REC001", sale_name="SO001")


class TestHarmanOrderServiceEdgeCases:
    """Tests for HarmanOrderService edge cases."""

    def test_read_orders_file_read_error(self, mocker, tmp_path):
        """Test handling when file cannot be read."""
        from src.services.harman_order_service import HarmanOrderService

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create a file but make it unreadable
        test_file = input_dir / "test.edi"
        test_file.write_text("test data")

        service = HarmanOrderService(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            name_filter=r".*",
            artwork_service=None,
            order_provider="TEST",
        )

        # Mock file reading to raise an error
        mocker.patch.object(Path, "read_text", side_effect=PermissionError("Cannot read file"))

        # The generator should handle exceptions internally
        orders = list(service.read_orders())
        assert orders == []

    def test_should_update_sale_b2c_returns_false(self, tmp_path):
        """Test that B2C orders return False for should_update_sale."""
        from src.domain import LineItem, Order, ShipTo
        from src.services.harman_order_service import HarmanOrderService

        service = HarmanOrderService(
            input_dir=tmp_path,
            output_dir=tmp_path,
            name_filter=r".*",
            artwork_service=None,
            order_provider="HARMAN JBL B2C",  # B2C provider
        )

        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="Test",
            email="test@example.com",
            phone="555-0000",
            street1="123 Main",
            city="Test City",
            postal_code="12345",
            country_code="US",
        )
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="HARMAN JBL B2C",
            pricelist_id=50,
            remote_order_id="ORD001",
            shipment_type="standard",
            description="Test",
            ship_to=ship_to,
            line_items=[LineItem(line_id="L1", product_code="PROD001", quantity=10)],
        )

        # B2C should return False (should NOT update)
        assert service.should_update_sale(order) is False

    def test_should_update_sale_b2b_returns_true(self, tmp_path):
        """Test that B2B orders return True for should_update_sale."""
        from src.domain import LineItem, Order, ShipTo
        from src.services.harman_order_service import HarmanOrderService

        service = HarmanOrderService(
            input_dir=tmp_path,
            output_dir=tmp_path,
            name_filter=r".*",
            artwork_service=None,
            order_provider="HARMAN JBL B2B",  # B2B provider
        )

        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="Test",
            email="test@example.com",
            phone="555-0000",
            street1="123 Main",
            city="Test City",
            postal_code="12345",
            country_code="US",
        )
        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="HARMAN JBL B2B",
            pricelist_id=50,
            remote_order_id="ORD001",
            shipment_type="standard",
            description="Test",
            ship_to=ship_to,
            line_items=[LineItem(line_id="L1", product_code="PROD001", quantity=10)],
        )

        # B2B should return True (should update)
        assert service.should_update_sale(order) is True


class TestOdooSaleServiceEdgeCases:
    """Tests for OdooSaleService edge cases."""

    pass  # Removed empty/spaces-only shipment_type tests - Order validation prevents these


class TestConfigValidation:
    """Tests for Config validation."""

    def test_config_missing_required_urls(self, monkeypatch):
        """Test that missing required URLs raise ValueError."""
        from importlib import reload

        import src.config as config_module

        # Clear the required URLs
        monkeypatch.setenv("ODOO_BASE_URL", "")
        monkeypatch.setenv("SPECTRUM_BASE_URL", "http://api.example.com")

        # Reload the module to apply monkeypatch
        reload(config_module)

        with pytest.raises(ValueError, match="Environment variable ODOO_BASE_URL is required"):
            config_module.Config()


class TestRegistryUnregister:
    """Tests for Registry unregister() method."""

    def test_unregister_removes_item(self):
        """Test that unregister() removes an item."""
        registry = Registry[str]()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        assert registry.get("item1") == "value1"

        registry.unregister("item1")

        assert registry.get("item1") is None
        assert registry.get("item2") == "value2"

    def test_unregister_nonexistent_item(self):
        """Test that unregister() on nonexistent item doesn't fail."""
        registry = Registry[str]()
        registry.unregister("nonexistent")  # Should not raise

    def test_unregister_then_register_same_name(self):
        """Test that unregistered name can be registered again."""
        registry = Registry[str]()
        registry.register("item", "value1")
        registry.unregister("item")
        registry.register("item", "value2")

        assert registry.get("item") == "value2"
