"""Shared fixtures for integration tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import httpx
import pytest

from src.app.odoo_auth import OdooAuth
from src.app.registry import Registry
from src.domain import LineItem, Order, ShipTo


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
def odoo_client(httpx_mock):
    """Provide an httpx.Client for Odoo with pytest_httpx mocking."""
    with httpx.Client(base_url="http://localhost:8069") as client:
        yield client


@pytest.fixture
def spectrum_client(httpx_mock):
    """Provide an httpx.Client for Spectrum with pytest_httpx mocking."""
    with httpx.Client(base_url="https://spectrum.example.com") as client:
        client.headers["SPECTRUM_API_TOKEN"] = "test_token"
        yield client


@pytest.fixture
def error_queue():
    """Provide a mock error queue."""
    queue = Mock()
    queue.queue = []

    def put_side_effect(item):
        queue.queue.append(item)

    queue.put = Mock(side_effect=put_side_effect)
    return queue


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
        remote_line_id="LI123",
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
