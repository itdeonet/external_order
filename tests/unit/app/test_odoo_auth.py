"""Unit tests for OdooAuth class."""

import pytest

from src.app.odoo_auth import OdooAuth


class TestOdooAuthInstantiation:
    """Tests for OdooAuth instantiation."""

    def test_instantiation_with_valid_data(self):
        """Test creating OdooAuth with valid data."""
        auth = OdooAuth(database="odoo_db", user_id=1, password="secret123")

        assert auth.database == "odoo_db"
        assert auth.user_id == 1
        assert auth.password == "secret123"

    def test_instantiation_with_all_fields_populated(self):
        """Test that all fields are stored correctly."""
        auth = OdooAuth(database="production_db", user_id=42, password="complex_password!")

        assert auth.database == "production_db"
        assert auth.user_id == 42
        assert auth.password == "complex_password!"

    def test_instantiation_creates_frozen_dataclass(self):
        """Test that OdooAuth is a frozen dataclass."""
        auth = OdooAuth(database="odoo_db", user_id=1, password="secret123")

        with pytest.raises(AttributeError):
            auth.database = "another_db"  # type: ignore

    def test_instantiation_with_whitespace_in_database(self):
        """Test that database with leading/trailing whitespace is accepted."""
        auth = OdooAuth(database="  odoo_db  ", user_id=1, password="secret123")
        assert auth.database == "  odoo_db  "


class TestOdooAuthValidation:
    """Tests for OdooAuth validation."""

    def test_rejects_empty_database(self):
        """Test that empty database is rejected."""
        with pytest.raises(ValueError, match="Database cannot be empty"):
            OdooAuth(database="", user_id=1, password="secret123")

    def test_rejects_whitespace_only_database(self):
        """Test that whitespace-only database is rejected."""
        with pytest.raises(ValueError, match="Database cannot be empty"):
            OdooAuth(database="   ", user_id=1, password="secret123")

    def test_rejects_non_string_database(self):
        """Test that non-string database is rejected."""
        with pytest.raises(ValueError, match="Database cannot be empty"):
            OdooAuth(database=None, user_id=1, password="secret123")  # type: ignore

    def test_rejects_zero_user_id(self):
        """Test that user_id of 0 is rejected."""
        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            OdooAuth(database="odoo_db", user_id=0, password="secret123")

    def test_rejects_negative_user_id(self):
        """Test that negative user_id is rejected."""
        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            OdooAuth(database="odoo_db", user_id=-5, password="secret123")

    def test_accepts_positive_user_id(self):
        """Test that positive user_id is accepted."""
        auth = OdooAuth(database="odoo_db", user_id=1, password="secret123")
        assert auth.user_id == 1

    def test_accepts_large_positive_user_id(self):
        """Test that large positive user_id is accepted."""
        auth = OdooAuth(database="odoo_db", user_id=999999, password="secret123")
        assert auth.user_id == 999999

    def test_rejects_empty_password(self):
        """Test that empty password is rejected."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            OdooAuth(database="odoo_db", user_id=1, password="")

    def test_rejects_whitespace_only_password(self):
        """Test that whitespace-only password is rejected."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            OdooAuth(database="odoo_db", user_id=1, password="   ")

    def test_rejects_non_string_password(self):
        """Test that non-string password is rejected."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            OdooAuth(database="odoo_db", user_id=1, password=None)  # type: ignore


class TestOdooAuthFromConfig:
    """Tests for from_config class method."""

    def test_from_config_creates_valid_instance(self, mocker):
        """Test creating OdooAuth from a config object."""
        mock_config = mocker.Mock()
        mock_config.odoo_database = "test_db"
        mock_config.odoo_rpc_user_id = 10
        mock_config.odoo_rpc_password = "test_password"

        auth = OdooAuth.from_config(mock_config)

        assert auth.database == "test_db"
        assert auth.user_id == 10
        assert auth.password == "test_password"

    def test_from_config_preserves_config_values(self, mocker):
        """Test that from_config preserves all values from config."""
        mock_config = mocker.Mock()
        mock_config.odoo_database = "production"
        mock_config.odoo_rpc_user_id = 42
        mock_config.odoo_rpc_password = "secure_pass"

        auth = OdooAuth.from_config(mock_config)

        assert auth.database == "production"
        assert auth.user_id == 42
        assert auth.password == "secure_pass"

    def test_from_config_validates_config_values(self, mocker):
        """Test that from_config validates the extracted values."""
        mock_config = mocker.Mock()
        mock_config.odoo_database = ""
        mock_config.odoo_rpc_user_id = 1
        mock_config.odoo_rpc_password = "pass"

        with pytest.raises(ValueError, match="Database cannot be empty"):
            OdooAuth.from_config(mock_config)

    def test_from_config_returns_frozen_instance(self, mocker):
        """Test that from_config returns a frozen instance."""
        mock_config = mocker.Mock()
        mock_config.odoo_database = "test_db"
        mock_config.odoo_rpc_user_id = 1
        mock_config.odoo_rpc_password = "pass"

        auth = OdooAuth.from_config(mock_config)

        with pytest.raises(AttributeError):
            auth.database = "another_db"  # type: ignore

    def test_from_config_with_numeric_user_id(self, mocker):
        """Test from_config with numeric user ID."""
        mock_config = mocker.Mock()
        mock_config.odoo_database = "test"
        mock_config.odoo_rpc_user_id = 123
        mock_config.odoo_rpc_password = "password"

        auth = OdooAuth.from_config(mock_config)
        assert auth.user_id == 123

    def test_from_config_with_invalid_user_id(self, mocker):
        """Test from_config with invalid user ID."""
        mock_config = mocker.Mock()
        mock_config.odoo_database = "test"
        mock_config.odoo_rpc_user_id = 0
        mock_config.odoo_rpc_password = "password"

        with pytest.raises(ValueError, match="User ID must be a positive integer"):
            OdooAuth.from_config(mock_config)
