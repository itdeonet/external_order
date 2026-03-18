"""Unit tests for SpectrumArtworkService."""

import io
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
import requests

from src.app.errors import ArtworkError
from src.domain import LineItem, Order, ShipTo
from src.services.spectrum_artwork_service import SpectrumArtworkService


def _create_mock_session():
    """Create a mock requests.Session with a proper headers attribute."""
    mock = Mock(spec=requests.Session)
    mock.headers = {}
    return mock


class TestSpectrumArtworkServiceInstantiation:
    """Tests for SpectrumArtworkService instantiation."""

    def test_instantiation_with_required_fields(self):
        """Test creating SpectrumArtworkService with required fields."""
        mock_client = _create_mock_session()
        digitals_dir = Path("/tmp/digitals")

        service = SpectrumArtworkService(
            session=mock_client,
            base_url="https://spectrum.example.com",
            digitals_dir=digitals_dir,
        )

        assert service.session is mock_client
        assert service.base_url == "https://spectrum.example.com"
        assert service.digitals_dir == digitals_dir

    def test_instantiation_with_defaults(self, mocker):
        """Test creating SpectrumArtworkService with config defaults."""
        mock_client = _create_mock_session()
        mock_config = Mock()
        mock_config.spectrum_base_url = "https://spectrum.default.com"
        mock_config.digitals_dir = "/default/digitals"
        mocker.patch("src.services.spectrum_artwork_service.get_config", return_value=mock_config)

        service = SpectrumArtworkService(session=mock_client)

        assert service.session is mock_client
        assert service.base_url == "https://spectrum.default.com"
        assert service.digitals_dir == Path("/default/digitals")

    def test_instantiation_initializes_empty_client(self):
        """Test that client is initialized as empty string."""
        mock_client = _create_mock_session()
        service = SpectrumArtworkService(
            session=mock_client,
            base_url="https://spectrum.example.com",
            digitals_dir=Path("/tmp"),
        )

        assert isinstance(service.client_handle, str)
        assert service.client_handle == ""

    def test_instantiation_initializes_empty_order_data(self):
        """Test that order_data is initialized as empty dict."""
        mock_client = _create_mock_session()
        service = SpectrumArtworkService(
            session=mock_client,
            base_url="https://spectrum.example.com",
            digitals_dir=Path("/tmp"),
        )

        assert isinstance(service.order_data, dict)
        assert service.order_data == {}

    def test_instantiation_raises_without_session(self):
        """Test that session is required."""
        with pytest.raises(TypeError):
            SpectrumArtworkService(base_url="https://spectrum.example.com")  # type: ignore

    def test_register_classmethod_creates_instance_with_defaults(self, mocker):
        """Test that register() classmethod creates instance with config defaults."""
        mock_client = _create_mock_session()
        mock_registry = Mock()
        mock_config = Mock()
        mock_config.spectrum_base_url = "https://spectrum.default.com"
        mock_config.digitals_dir = "/default/digitals"

        mocker.patch(
            "src.services.spectrum_artwork_service.get_artwork_services", return_value=mock_registry
        )
        mocker.patch("src.services.spectrum_artwork_service.get_config", return_value=mock_config)

        SpectrumArtworkService.register("spectrum_artwork", mock_client, "test-api-key")

        # Verify headers were updated with API key
        assert mock_client.headers.get("SPECTRUM_API_TOKEN") == "test-api-key"

        # Verify register was called
        mock_registry.register.assert_called_once()
        call_args = mock_registry.register.call_args
        assert call_args[0][0] == "spectrum_artwork"
        assert isinstance(call_args[0][1], SpectrumArtworkService)

    def test_register_classmethod_registers_with_provided_session(self, mocker):
        """Test that register() classmethod registers instance with provided session."""
        mock_client = _create_mock_session()
        mock_registry = Mock()
        mock_config = Mock()
        mock_config.spectrum_base_url = "https://spectrum.default.com"
        mock_config.digitals_dir = "/default/digitals"

        mocker.patch(
            "src.services.spectrum_artwork_service.get_artwork_services", return_value=mock_registry
        )
        mocker.patch("src.services.spectrum_artwork_service.get_config", return_value=mock_config)

        service_name = "test_artwork_service"
        api_key = "test-api-key-123"
        SpectrumArtworkService.register(service_name, mock_client, api_key)

        # Verify the service was registered with the provided session
        mock_registry.register.assert_called_once()
        registered_name, registered_service = mock_registry.register.call_args[0]
        assert registered_name == service_name
        assert registered_service.session is mock_client

    def test_register_classmethod_updates_session_headers(self, mocker):
        """Test that register() classmethod updates session headers with API key."""
        mock_client = _create_mock_session()
        mock_registry = Mock()
        mock_config = Mock()
        mock_config.spectrum_base_url = "https://spectrum.default.com"
        mock_config.digitals_dir = "/default/digitals"

        mocker.patch(
            "src.services.spectrum_artwork_service.get_artwork_services", return_value=mock_registry
        )
        mocker.patch("src.services.spectrum_artwork_service.get_config", return_value=mock_config)

        api_key = "my-secret-api-key"
        SpectrumArtworkService.register("spectrum_art", mock_client, api_key)

        # Verify correct header was set
        assert mock_client.headers["SPECTRUM_API_TOKEN"] == api_key


class TestSpectrumArtworkServiceClientAttribute:
    """Tests for the client attribute."""

    def test_client_is_initialized_empty(self):
        """Test that client starts as empty string."""
        mock_client = _create_mock_session()
        service = SpectrumArtworkService(
            session=mock_client,
            base_url="https://spectrum.example.com",
            digitals_dir=Path("/tmp"),
        )

        assert service.client_handle == ""

    def test_client_cannot_be_set_directly_frozen(self):
        """Test that service is frozen and client cannot be modified directly."""
        mock_client = _create_mock_session()
        service = SpectrumArtworkService(
            session=mock_client,
            base_url="https://spectrum.example.com",
            digitals_dir=Path("/tmp"),
        )

        with pytest.raises(Exception):  # FrozenInstanceError  # noqa: B017
            service.client_handle = "NEW_CLIENT"  # type: ignore

    def test_client_cannot_be_passed_as_init_parameter(self):
        """Test that client cannot be initialized via __init__."""
        mock_client = _create_mock_session()
        with pytest.raises(TypeError):
            SpectrumArtworkService(
                session=mock_client,
                base_url="https://spectrum.example.com",
                digitals_dir=Path("/tmp"),
                client_handle="CLIENT123",  # type: ignore
            )


class TestSpectrumArtworkServiceGetArtwork:
    """Tests for the get_artwork method."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked requests.Session."""
        return _create_mock_session()

    @pytest.fixture
    def service(self, mock_client, tmp_path):
        """Provide a SpectrumArtworkService instance."""
        return SpectrumArtworkService(
            session=mock_client,
            base_url="https://spectrum.example.com",
            digitals_dir=tmp_path,
        )

    @pytest.fixture
    def basic_order(self):
        """Provide a basic Order instance."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD001", quantity=100)

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_sale_id(12345)
        return order

    def _setup_mock_client_for_get_artwork(self, mock_client, mocker):
        """Helper to setup mock client for get_artwork calls with design zip and placement PDF."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            """Return different responses based on URL."""
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                # Design zip file response
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                # Placement PDF response
                response.content = placement_bytes
            else:
                # Order API response
                response.json.return_value = {
                    "clientHandle": "CLIENT123",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                            "recipeSetId": "RECIPE001",
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

    def test_get_artwork_fetches_from_api(self, service, mock_client, basic_order, mocker):
        """Test that get_artwork fetches from the correct API endpoint."""
        self._setup_mock_client_for_get_artwork(mock_client, mocker)

        service.get_artwork(basic_order)

        # Verify the order API was called with correct endpoint
        calls = mock_client.get.call_args_list
        assert any(
            call[1].get("url") == "https://spectrum.example.com/api/order/order-number/HA-EM-12345/"
            for call in calls
        )

    def test_get_artwork_sets_client_handle(self, service, mock_client, basic_order, mocker):
        """Test that get_artwork sets the client from response."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "clientHandle": "SPECTRUM_CLIENT",
            "lineItems": [
                {
                    "id": 1,
                    "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                    "recipeSetId": "RECIPE001",
                }
            ],
        }

        # Setup different responses based on URL
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                response.json.return_value = {
                    "clientHandle": "SPECTRUM_CLIENT",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                            "recipeSetId": "RECIPE001",
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        service.get_artwork(basic_order)

        assert service.client_handle == "SPECTRUM_CLIENT"

    def test_get_artwork_creates_artwork_object(self, service, mock_client, basic_order, mocker):
        """Test that get_artwork creates Artwork object for each line item."""
        self._setup_mock_client_for_get_artwork(mock_client, mocker)

        service.get_artwork(basic_order)

        # Line item should have artwork set
        line_item = basic_order.line_items[0]
        assert line_item.artwork is not None
        assert line_item.artwork.artwork_id == "RECIPE001"

    def test_get_artwork_raises_for_missing_artwork(self, service, mock_client, basic_order):
        """Test that get_artwork raises ArtworkError if no artwork found."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "clientHandle": "CLIENT123",
            "lineItems": [
                {
                    "id": 1,
                    "skuQuantities": [{"sku": "DIFFERENT_PROD", "quantity": 100}],
                    "recipeSetId": "RECIPE001",
                }
            ],
        }
        mock_client.get.return_value = mock_response

        with pytest.raises(ArtworkError, match="No artwork found"):
            service.get_artwork(basic_order)

    def test_get_artwork_raises_when_api_returns_no_line_items(
        self, service, mock_client, basic_order
    ):
        """Test that get_artwork raises error when API returns no line items."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "clientHandle": "CLIENT123",
            "lineItems": [],  # Empty list
        }
        mock_client.get.return_value = mock_response

        with pytest.raises(ArtworkError, match="No artwork found"):
            service.get_artwork(basic_order)

    def test_get_artwork_raises_when_recipe_set_id_is_missing(
        self, service, mock_client, basic_order, mocker
    ):
        """Test that get_artwork raises error when recipeSetId is missing from API."""
        # Setup with different responses based on URL
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                response.json.return_value = {
                    "clientHandle": "CLIENT123",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                            "recipeSetId": None,  # Missing or null
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            service.get_artwork(basic_order)

    def test_get_artwork_raises_when_sku_quantities_is_empty(
        self, service, mock_client, basic_order
    ):
        """Test that get_artwork raises error when skuQuantities is empty."""
        mock_response = Mock(spec=requests.Response)
        mock_response.json.return_value = {
            "clientHandle": "CLIENT123",
            "lineItems": [
                {
                    "id": 1,
                    "skuQuantities": [],  # Empty list
                    "recipeSetId": "RECIPE001",
                }
            ],
        }
        mock_client.get.return_value = mock_response

        with pytest.raises(ArtworkError, match="No artwork found"):
            service.get_artwork(basic_order)

    def test_get_artwork_sets_empty_client_when_missing_from_response(
        self, service, mock_client, basic_order, mocker
    ):
        """Test that client is set to empty string if not in API response."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                # No clientHandle in response
                response.json.return_value = {
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                            "recipeSetId": "RECIPE001",
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        service.get_artwork(basic_order)

        # Client should be empty string when not provided
        assert service.client_handle == ""

    def test_get_artwork_with_multiple_skus_in_single_line_item(
        self, service, mock_client, tmp_path, mocker
    ):
        """Test get_artwork when a line item has multiple SKU quantities."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item = LineItem(line_id="RL-001", product_code="PROD001", quantity=100)

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-55555",
            shipment_type="standard",
            ship_to=ship_to,
            description="Test order",
            line_items=[line_item],
        )
        order.set_sale_id(55555)

        # Setup mock client with multiple SKU quantities in response
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                response.json.return_value = {
                    "clientHandle": "CLIENT789",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [
                                {"sku": "PROD001", "quantity": 100},
                                {"sku": "PROD002", "quantity": 50},
                            ],
                            "recipeSetId": "RECIPE001",
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        service.get_artwork(order)

        # Should match PROD001 with quantity 100
        assert line_item.artwork is not None
        assert line_item.artwork.artwork_id == "RECIPE001"

    def test_get_artwork_returns_empty_list(self, service, mock_client, basic_order, mocker):
        """Test that get_artwork returns a list of file paths when artwork is found."""
        self._setup_mock_client_for_get_artwork(mock_client, mocker)

        result = service.get_artwork(basic_order)

        # Should return file paths for design and placement files
        assert len(result) > 0
        assert all(isinstance(p, Path) for p in result)

    def test_get_artwork_calls_download_designs(self, service, mock_client, basic_order, mocker):
        """Test that get_artwork successfully retrieves and sets design files."""
        # Setup mock to properly return responses with real design file
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                response.json.return_value = {
                    "clientHandle": "CLIENT123",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                            "recipeSetId": "RECIPE001",
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        service.get_artwork(basic_order)

        # Verify designs were retrieved - check the artwork has design paths
        artwork = basic_order.line_items[0].artwork
        assert artwork is not None
        assert len(artwork.design_paths) > 0
        # Verify the design file was saved
        assert artwork.design_paths[0].exists()

    def test_get_artwork_calls_download_placement(self, service, mock_client, basic_order, mocker):
        """Test that get_artwork successfully retrieves and sets placement file."""
        # Setup mock to properly return responses
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                response.json.return_value = {
                    "clientHandle": "CLIENT123",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                            "recipeSetId": "RECIPE001",
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        service.get_artwork(basic_order)

        # Verify placement was retrieved - check the artwork has placement path
        artwork = basic_order.line_items[0].artwork
        assert artwork is not None
        assert artwork.placement_path is not None
        # Verify the placement file was saved
        assert artwork.placement_path.exists()

    def test_get_artwork_with_multiple_line_items(self, service, mock_client, tmp_path, mocker):
        """Test get_artwork with multiple line items."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )
        line_item1 = LineItem(line_id="RL-001", product_code="PROD001", quantity=50)
        line_item2 = LineItem(line_id="RL-002", product_code="PROD002", quantity=75)

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-99999",
            shipment_type="standard",
            description="Test order",
            ship_to=ship_to,
            line_items=[line_item1, line_item2],
        )
        order.set_sale_id(99999)

        # Setup mock client to return different responses based on URL
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                response.json.return_value = {
                    "clientHandle": "CLIENT456",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 50}],
                            "recipeSetId": "RECIPE101",
                        },
                        {
                            "id": 2,
                            "skuQuantities": [{"sku": "PROD002", "quantity": 75}],
                            "recipeSetId": "RECIPE102",
                        },
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        service.get_artwork(order)

        assert service.client_handle == "CLIENT456"
        assert line_item1.artwork is not None
        assert line_item2.artwork is not None
        assert line_item1.artwork.artwork_id == "RECIPE101"
        assert line_item2.artwork.artwork_id == "RECIPE102"

    def test_get_artwork_handles_quantity_exact_match_when_api_returns_different_value(
        self, service, mock_client, basic_order, mocker
    ):
        """Test that quantity-1 combinations don't match when exact quantity is available."""
        # The service adds combinations for: quantity, quantity-1, and 1
        # This test verifies that when exact match is available, it's used
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)
        design_zip_bytes = zip_buffer.getvalue()

        placement_bytes = b"PDF placement content"

        def mock_get_side_effect(url=None, **kwargs):
            response = Mock(spec=requests.Response)
            if url and "webtoprint" in url:
                response.content = design_zip_bytes
            elif url and "pdf" in url:
                response.content = placement_bytes
            else:
                # API returns exact quantity match
                response.json.return_value = {
                    "clientHandle": "CLIENT789",
                    "lineItems": [
                        {
                            "id": 1,
                            "skuQuantities": [{"sku": "PROD001", "quantity": 100}],
                            "recipeSetId": "RECIPE001",
                        }
                    ],
                }
            return response

        mock_client.get.side_effect = mock_get_side_effect

        # Should find artwork with exact quantity match
        service.get_artwork(basic_order)
        assert basic_order.line_items[0].artwork is not None

    def test_download_placement_downloads_pdf(self, service, mock_client):
        """Test that _download_placement downloads and saves PDF file."""
        placement_content = b"PDF content for placement"
        mock_response = Mock(spec=requests.Response)
        mock_response.content = placement_content
        mock_client.get.return_value = mock_response

        placement_path = service._download_placement(
            recipe_set_id="RECIPE001", sale_name="SO-12345"
        )

        assert placement_path.exists()
        assert placement_path.read_bytes() == placement_content
        mock_response.raise_for_status.assert_called_once()

    def test_download_placement_saves_with_correct_filename(self, service, mock_client, tmp_path):
        """Test that placement file is saved with sale_name prefix."""
        placement_content = b"PDF content"
        mock_response = Mock(spec=requests.Response)
        mock_response.content = placement_content
        mock_client.get.return_value = mock_response

        placement_path = service._download_placement(
            recipe_set_id="RECIPE001", sale_name="SO-12345"
        )

        assert "SO-12345_RECIPE001_placement.pdf" in str(placement_path)
        assert tmp_path in placement_path.parents

    def test_download_placement_saves_to_digitals_dir(self, service, mock_client, tmp_path):
        """Test that placement is saved to digitals_dir."""
        placement_content = b"PDF content"
        mock_response = Mock(spec=requests.Response)
        mock_response.content = placement_content
        mock_client.get.return_value = mock_response

        service._download_placement(recipe_set_id="RECIPE001", sale_name="SO-999")

        assert (tmp_path / "SO-999_RECIPE001_placement.pdf").exists()

    def test_download_placement_raises_on_http_error(self, service, mock_client):
        """Test that HTTP errors are wrapped in ArtworkError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        http_error = requests.exceptions.HTTPError("404 Not Found")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_client.get.return_value = mock_response

        with pytest.raises(ArtworkError):
            service._download_placement(recipe_set_id="RECIPE001", sale_name="SO-12345")

    def test_download_placement_returns_path(self, service, mock_client):
        """Test that _download_placement returns a Path object."""
        placement_content = b"PDF content"
        mock_response = Mock(spec=requests.Response)
        mock_response.content = placement_content
        mock_client.get.return_value = mock_response

        result = service._download_placement(recipe_set_id="RECIPE001", sale_name="SO-12345")

        assert isinstance(result, Path)

    def test_download_placement_with_different_recipe_ids(self, service, mock_client, tmp_path):
        """Test that different recipe IDs create different filenames."""
        placement_content = b"PDF content"
        mock_response = Mock(spec=requests.Response)
        mock_response.content = placement_content
        mock_client.get.return_value = mock_response

        service._download_placement(recipe_set_id="ART456", sale_name="SO-111")

        assert (tmp_path / "SO-111_ART456_placement.pdf").exists()

    def test_download_placement_calls_correct_endpoint(self, service, mock_client):
        """Test that _download_placement calls API with correct endpoint structure."""
        placement_content = b"PDF content"
        mock_response = Mock(spec=requests.Response)
        mock_response.content = placement_content
        mock_client.get.return_value = mock_response

        service._download_placement(recipe_set_id="ART123", sale_name="SO-456")

        # Verify the endpoint was called - the exact URL depends on service.client which is empty by default
        # Verify get was called at least once with a URL containing the recipe ID
        calls = mock_client.get.call_args_list
        assert len(calls) > 0
        assert any("ART123" in str(call) for call in calls)

    def test_download_designs_downloads_zip(self, service, mock_client):
        """Test that _download_designs downloads and extracts zip file."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design1.pdf", "design content 1")
            zip_file.writestr("design2.pdf", "design content 2")
        zip_buffer.seek(0)

        mock_response = Mock(spec=requests.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        saved_paths = service._download_designs(recipe_set_id="RECIPE001", sale_name="SO-12345")

        assert len(saved_paths) == 2
        mock_client.get.assert_called_once_with(
            url="https://spectrum.example.com/api/webtoprint/RECIPE001/", timeout=(5, 30)
        )
        mock_response.raise_for_status.assert_called_once()

    def test_download_designs_saves_with_correct_filename(self, service, mock_client, tmp_path):
        """Test that files are saved with sale_name prefix."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)

        mock_response = Mock(spec=requests.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        saved_paths = service._download_designs(recipe_set_id="RECIPE001", sale_name="SO-12345")

        assert len(saved_paths) == 1
        assert "SO-12345_design.pdf" in str(saved_paths[0])
        assert tmp_path in saved_paths[0].parents

    def test_download_designs_saves_to_digitals_dir(self, service, mock_client, tmp_path):
        """Test that designs are saved to digitals_dir."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)

        mock_response = Mock(spec=requests.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        saved_paths = service._download_designs(recipe_set_id="RECIPE001", sale_name="SO-999")

        assert len(saved_paths) == 1
        assert (tmp_path / "SO-999_design.pdf").exists()

    def test_download_designs_handles_multiple_files(self, service, mock_client):
        """Test that multiple files in zip are all extracted."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            for i in range(5):
                zip_file.writestr(f"design_{i}.pdf", f"content {i}")
        zip_buffer.seek(0)

        mock_response = Mock(spec=requests.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        saved_paths = service._download_designs(recipe_set_id="RECIPE001", sale_name="SO-12345")

        assert len(saved_paths) == 5

    def test_download_designs_raises_on_http_error(self, service, mock_client):
        """Test that HTTP errors are wrapped in ArtworkError."""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        http_error = requests.exceptions.HTTPError("404 Not Found")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_client.get.return_value = mock_response

        with pytest.raises(ArtworkError):
            service._download_designs(recipe_set_id="RECIPE001", sale_name="SO-12345")

    def test_download_designs_calls_correct_endpoint(self, service, mock_client):
        """Test that _download_designs calls the correct API endpoint."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "content")
        zip_buffer.seek(0)

        mock_response = Mock(spec=requests.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        service._download_designs(recipe_set_id="ART123", sale_name="SO-456")

        mock_client.get.assert_called_once_with(
            url="https://spectrum.example.com/api/webtoprint/ART123/", timeout=(5, 30)
        )

    def test_download_designs_returns_list_of_paths(self, service, mock_client):
        """Test that _download_designs returns list of Path objects."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "content")
        zip_buffer.seek(0)

        mock_response = Mock(spec=requests.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        result = service._download_designs(recipe_set_id="RECIPE001", sale_name="SO-12345")

        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)

    def test_download_designs_with_different_sale_names(self, service, mock_client, tmp_path):
        """Test that different sale names create different filenames."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "content")
        zip_buffer.seek(0)

        mock_response = Mock(spec=requests.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        service._download_designs(recipe_set_id="RECIPE001", sale_name="SO-111")

        assert (tmp_path / "SO-111_design.pdf").exists()
