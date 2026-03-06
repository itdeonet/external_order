"""Unit tests for OdooAuth class."""

from types import SimpleNamespace

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

    def test_instantiation_with_all_default_values(self, monkeypatch):
        """Test that OdooAuth can use default factory values from config."""
        import src.app.odoo_auth as odoo_module

        monkeypatch.setattr(
            odoo_module,
            "get_config",
            lambda: SimpleNamespace(
                odoo_database="test_db", odoo_rpc_user_id=5, odoo_rpc_password="test_pw"
            ),
        )

        auth = OdooAuth()

        assert auth.database == "test_db"
        assert auth.user_id == 5
        assert auth.password == "test_pw"


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

    def test_rejects_default_values_from_invalid_config(self, monkeypatch):
        """Test that default factory values are validated."""
        import src.app.odoo_auth as odoo_module

        monkeypatch.setattr(
            odoo_module,
            "get_config",
            lambda: SimpleNamespace(odoo_database="", odoo_rpc_user_id=1, odoo_rpc_password="pw"),
        )

        with pytest.raises(ValueError, match="Database cannot be empty"):
            OdooAuth()
