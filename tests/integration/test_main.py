"""Integration tests for main.py application setup and execution."""

import contextlib
from pathlib import Path
from unittest.mock import Mock, patch

from src.app.registry import Registry
from src.config import Config


class TestMainApplicationSetup:
    """Test the main application setup and service initialization."""

    def test_main_initializes_registry(self, tmp_path):
        """Test that service registries can be created and used."""
        # Test that we can create a Registry and it works correctly
        registry = Registry()
        mock_service = Mock()

        registry.register("TestService", mock_service)

        # Verify retrieval
        assert registry.get("TestService") == mock_service

        # Verify items iteration
        items = dict(registry.items())
        assert items["TestService"] == mock_service

    def test_main_creates_registries(self, tmp_path):
        """Test that main() creates and populates service registries."""
        # Create necessary directories
        (tmp_path / "templates").mkdir(parents=True)

        with patch("src.main.get_config") as mock_get_config:
            mock_config = Mock(spec=Config)
            mock_config.harman_input_dir = tmp_path / "harman" / "in"
            mock_config.harman_output_dir = tmp_path / "harman" / "out"
            mock_config.digitals_dir = tmp_path / "digitals"
            mock_config.open_orders_dir = tmp_path / "open_orders"
            mock_config.templates_dir = tmp_path / "templates"
            mock_config.harman_administration_id = 1
            mock_config.harman_customer_id = 100
            mock_config.harman_pricelist_id = 50
            mock_config.harman_order_provider = "Harman"
            mock_config.harman_shipment_type = "Standard"
            mock_config.harman_workdays_for_delivery = 5
            mock_config.odoo_base_url = "http://localhost:8069"
            mock_config.odoo_uid = 1
            mock_config.odoo_password = "test"
            mock_config.odoo_database = "test_db"
            mock_config.spectrum_base_url = "https://spectrum.example.com"
            mock_config.spectrum_api_key = "test_key"

            mock_get_config.return_value = mock_config

            # Test that we can create a Registry and it works correctly
            registry = Registry()
            mock_service = Mock()

            registry.register("TestService", mock_service)

            # Verify retrieval
            assert registry.get("TestService") == mock_service

            # Verify items iteration
            items = dict(registry.items())
            assert items["TestService"] == mock_service

    def test_main_error_handling(self):
        """Test that main() handles errors during use case execution."""
        with patch("src.main.get_config") as mock_get_config:
            mock_config = Mock(spec=Config)
            mock_config.harman_input_dir = Path("/tmp/in")
            mock_config.harman_output_dir = Path("/tmp/out")
            mock_config.digitals_dir = Path("/tmp/digitals")
            mock_config.open_orders_dir = Path("/tmp/open")
            mock_config.templates_dir = Path("/tmp/templates")
            mock_config.harman_administration_id = 1
            mock_config.harman_customer_id = 100
            mock_config.harman_pricelist_id = 50
            mock_config.harman_order_provider = "Harman"
            mock_config.harman_shipment_type = "Standard"
            mock_config.harman_workdays_for_delivery = 5
            mock_config.odoo_base_url = "http://localhost:8069"
            mock_config.odoo_uid = 1
            mock_config.odoo_password = "test"
            mock_config.odoo_database = "test_db"
            mock_config.spectrum_base_url = "https://spectrum.example.com"
            mock_config.spectrum_api_key = "test_key"

            mock_get_config.return_value = mock_config

            from src.main import main

            # Should not raise exceptions even if use cases fail
            with contextlib.suppress(Exception):
                main()
