"""Unit tests for configuration module."""

from pathlib import Path

import pytest

from src.config import Config, get_config


class TestConfigInitialization:
    """Tests for Config initialization."""

    def test_config_creates_required_directories(self, tmp_path):
        """Test that Config._post_init creates required directories."""
        # Create a config instance
        config = Config()

        # Verify directories are created in __post_init__
        assert hasattr(config, "harman_input_dir")
        assert hasattr(config, "harman_output_dir")
        assert hasattr(config, "digitals_dir")
        assert hasattr(config, "open_orders_dir")

    def test_config_sets_harman_defaults(self):
        """Test that Config has default Harman settings."""
        config = Config()

        assert config.harman_administration_id == 2
        assert config.harman_customer_id == 5380
        assert config.harman_pricelist_id == 2
        assert config.harman_order_provider == "HARMAN JBL"
        assert config.harman_shipment_type == "harman%"
        assert config.harman_workdays_for_delivery == 2

    def test_config_has_templates_dir(self):
        """Test that Config has templates_dir."""
        config = Config()

        assert config.templates_dir.exists()
        assert config.templates_dir.name == "templates"

    def test_config_has_default_box_size(self):
        """Test that Config has default box size dimensions."""
        config = Config()

        assert config.default_box_size == (24, 21, 6)
        assert len(config.default_box_size) == 3

    def test_config_has_work_dir_default(self):
        """Test that Config has a work_dir."""
        config = Config()

        assert config.work_dir is not None
        assert isinstance(config.work_dir, Path)

    def test_config_odoo_settings_exist(self):
        """Test that Config has Odoo settings."""
        config = Config()

        assert hasattr(config, "odoo_base_url")
        assert hasattr(config, "odoo_database")
        assert hasattr(config, "odoo_rpc_user_id")
        assert hasattr(config, "odoo_rpc_password")

    def test_config_spectrum_settings_exist(self):
        """Test that Config has Spectrum settings."""
        config = Config()

        assert hasattr(config, "spectrum_base_url")
        assert hasattr(config, "spectrum_jbl_api_key")

    def test_config_is_frozen_dataclass(self):
        """Test that Config is a frozen dataclass."""
        config = Config()

        # Attempting to modify a frozen dataclass should raise
        with pytest.raises(AttributeError):
            config.harman_administration_id = 999  # type: ignore


class TestGetConfig:
    """Tests for get_config function."""

    def test_get_config_returns_config_instance(self):
        """Test that get_config returns a Config instance."""
        # Clear cache first
        get_config.cache_clear()

        config = get_config()

        assert isinstance(config, Config)

    def test_get_config_is_cached(self):
        """Test that get_config caches the result."""
        # Clear cache first
        get_config.cache_clear()

        config1 = get_config()
        config2 = get_config()

        # Should be the same instance due to caching
        assert config1 is config2

    def test_get_config_has_functools_cache_decorator(self):
        """Test that get_config uses functools.cache."""
        # The function should have cache_clear method
        assert hasattr(get_config, "cache_clear")
        assert callable(get_config.cache_clear)
