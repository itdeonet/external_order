"""Shared fixtures for integration tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest
import requests

from src.app.errors import ErrorStore
from src.app.odoo_auth import OdooAuth
from src.app.registry import (
    Registry,
    get_artwork_services,
    get_order_services,
    get_sale_services,
    get_stock_services,
    get_use_cases,
)
from src.domain import LineItem, Order, ShipTo


@pytest.fixture(autouse=True)
def clear_registry_caches():
    """Clear all cached registries before each test to prevent test pollution.

    This fixture runs automatically before each test and clears the singleton
    caches created by functools.cache decorator on the registry getter functions.
    """
    yield  # Run test first
    # Clear caches after test to ensure clean state for next test
    get_artwork_services.cache_clear()
    get_order_services.cache_clear()
    get_sale_services.cache_clear()
    get_stock_services.cache_clear()
    get_use_cases.cache_clear()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def odoo_auth():
    """Provide a mock OdooAuth instance."""
    auth = Mock(spec=OdooAuth)
    auth.database = "test_db"
    auth.user_id = 1
    auth.password = "test_password"
    return auth


@pytest.fixture
def odoo_client():
    """Provide a requests.Session for Odoo."""
    return requests.Session()


@pytest.fixture
def spectrum_client(httpx_mock):
    """Provide an httpx.Client for Spectrum with pytest_httpx mocking."""
    with requests.Session() as session:
        session.headers["SPECTRUM_API_TOKEN"] = "test_token"
        yield session


@pytest.fixture
def error_store(mocker):
    """Provide a mock error store and patch it in modules that use it."""
    mock_store = Mock(spec=ErrorStore)
    # Patch get_error_store in all use case modules
    mocker.patch("src.app.completed_sale_use_case.get_error_store", return_value=mock_store)
    mocker.patch("src.app.new_sale_use_case.get_error_store", return_value=mock_store)
    mocker.patch("src.app.stock_transfer_use_case.get_error_store", return_value=mock_store)
    return mock_store


@pytest.fixture
def sample_ship_to():
    """Provide a sample ShipTo instance."""
    return ShipTo(
        remote_customer_id="CUST123",
        contact_name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        street1="123 Main St",
        street2="Suite 100",
        city="Springfield",
        state="IL",
        postal_code="62701",
        country_code="US",
    )


@pytest.fixture
def sample_line_item():
    """Provide a sample LineItem instance."""
    return LineItem(
        line_id="LI123",
        product_code="PROD001",
        quantity=100,
    )


@pytest.fixture
def sample_order(sample_ship_to, sample_line_item):
    """Provide a sample Order instance."""
    return Order(
        administration_id=1,
        customer_id=123,
        order_provider="Harman",
        pricelist_id=1,
        remote_order_id="ORDER123",
        shipment_type="Standard",
        description="Test order",
        ship_to=sample_ship_to,
        line_items=[sample_line_item],
    )


@pytest.fixture
def order_services_registry():
    """Provide a mock order services registry."""
    registry = Mock(spec=Registry)
    registry.items.return_value = []
    return registry


@pytest.fixture
def artwork_services_registry():
    """Provide a mock artwork services registry."""
    registry = Mock(spec=Registry)
    registry.items.return_value = []
    return registry


@pytest.fixture
def stock_services_registry():
    """Provide a mock stock services registry."""
    registry = Mock(spec=Registry)
    registry.items.return_value = []
    return registry
