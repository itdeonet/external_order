"""Unit tests for SpectrumArtworkService."""

import io
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import httpx
import pytest

from src.domain.line_item import LineItem
from src.domain.order import Order
from src.domain.ship_to import ShipTo
from src.services.spectrum_artwork_service import SpectrumArtworkService


class TestSpectrumArtworkServiceInstantiation:
    """Tests for SpectrumArtworkService instantiation."""

    def test_instantiation_with_all_fields(self):
        """Test creating SpectrumArtworkService with all fields."""
        mock_client = Mock(spec=httpx.Client)
        digitals_dir = Path("/tmp/digitals")

        service = SpectrumArtworkService(engine=mock_client, digitals_dir=digitals_dir)

        assert service._engine is mock_client
        assert service._digitals_dir == digitals_dir
        assert service._client == ""

    def test_instantiation_initializes_empty_client(self):
        """Test that _client is initialized as empty string."""
        mock_client = Mock(spec=httpx.Client)
        service = SpectrumArtworkService(engine=mock_client, digitals_dir=Path("/tmp"))

        assert isinstance(service._client, str)
        assert service._client == ""


class TestSpectrumArtworkServiceGetArtworkIds:
    """Tests for get_artwork_ids method."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked httpx.Client."""
        return Mock(spec=httpx.Client)

    @pytest.fixture
    def service(self, mock_client):
        """Provide a SpectrumArtworkService instance."""
        return SpectrumArtworkService(engine=mock_client, digitals_dir=Path("/tmp/digitals"))

    @pytest.fixture
    def order(self, mocker):
        """Provide an Order instance with line items."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.product_id = "PROD001"
        line_item.quantity = 100

        return Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

    def test_get_artwork_ids_successful(self, service, mock_client, order, mocker):
        """Test getting artwork IDs with successful response."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "clientHandle": "CLIENT123",
            "line_items": [
                {"skuQuantities": [{"sku": "PROD001", "quantity": 100}], "recipeSetId": "RECIPE001"}
            ],
        }
        mock_client.get.return_value = mock_response
        spy_get = mocker.spy(mock_client, "get")
        spy_raise = mocker.spy(mock_response, "raise_for_status")
        service.get_artwork_ids(order)

        assert service._client == "CLIENT123"
        spy_get.assert_called_once_with(url="/api/order/order-number/HA-EM-12345/")
        spy_raise.assert_called_once()

    def test_get_artwork_ids_sets_artwork_ids_on_line_items(
        self, service, mock_client, order, mocker
    ):
        """Test that artwork IDs are set on matching line items."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "clientHandle": "CLIENT123",
            "line_items": [
                {"skuQuantities": [{"sku": "PROD001", "quantity": 100}], "recipeSetId": "RECIPE001"}
            ],
        }
        mock_client.get.return_value = mock_response

        spy = mocker.spy(order.line_items[0], "set_artwork_id")
        service.get_artwork_ids(order)
        spy.assert_called_once_with("RECIPE001")

    def test_get_artwork_ids_matches_by_quantity_minus_one(self, service, mock_client, mocker):
        """Test that artwork IDs match with quantity - 1 (workaround for +1 issue)."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.product_id = "PROD002"
        line_item.quantity = 50

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-54321",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

        mock_response = Mock(spec=httpx.Response)
        # API returns quantity 51 (one more than actual)
        mock_response.json.return_value = {
            "clientHandle": "CLIENT456",
            "line_items": [
                {"skuQuantities": [{"sku": "PROD002", "quantity": 51}], "recipeSetId": "RECIPE002"}
            ],
        }
        mock_client.get.return_value = mock_response
        spy = mocker.spy(order.line_items[0], "set_artwork_id")
        service.get_artwork_ids(order)
        spy.assert_called_once_with("RECIPE002")

    def test_get_artwork_ids_raises_on_http_error(self, service, mock_client, order, mocker):
        """Test that HTTP errors are raised."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            service.get_artwork_ids(order)

    def test_get_artwork_ids_handles_empty_line_items(self, service, mock_client, order, mocker):
        """Test that empty line_items in response are handled."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"clientHandle": "CLIENT789", "line_items": []}
        mock_client.get.return_value = mock_response

        service.get_artwork_ids(order)

        assert service._client == "CLIENT789"
        spy = mocker.spy(order.line_items[0], "set_artwork_id")
        service.get_artwork_ids(order)
        spy.assert_not_called()

    def test_get_artwork_ids_handles_no_matching_line_item(self, service, mock_client, mocker):
        """Test that unmatched artwork is not set."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.product_id = "DIFFERENT_PROD"
        line_item.quantity = 50

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-99999",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )

        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "clientHandle": "CLIENT111",
            "line_items": [
                {"skuQuantities": [{"sku": "PROD001", "quantity": 100}], "recipeSetId": "RECIPE001"}
            ],
        }
        mock_client.get.return_value = mock_response
        spy = mocker.spy(order.line_items[0], "set_artwork_id")
        service.get_artwork_ids(order)
        spy.assert_not_called()


class TestSpectrumArtworkServiceGetDesigns:
    """Tests for _get_designs method."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked httpx.Client."""
        mock = Mock(spec=httpx.Client)
        mock.base_url = "https://spectrum.example.com"
        return mock

    @pytest.fixture
    def service(self, mock_client, tmp_path):
        """Provide a SpectrumArtworkService instance."""
        return SpectrumArtworkService(engine=mock_client, digitals_dir=tmp_path)

    @pytest.fixture
    def order_with_artwork_id(self, mocker):
        """Provide an Order with line items that have artwork IDs."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.artwork_id = "ARTWORK001"
        line_item.product_id = "PROD001"
        line_item.quantity = 100

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(12345)
        return order

    def test_get_designs_downloads_and_extracts_zip(
        self, service, mock_client, order_with_artwork_id, tmp_path, mocker
    ):
        """Test that designs are downloaded and extracted from zip."""
        # Create a test zip file in memory
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design1.pdf", "design content 1")
            zip_file.writestr("design2.pdf", "design content 2")
        zip_buffer.seek(0)

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        spy_get = mocker.spy(mock_client, "get")
        spy_raise = mocker.spy(mock_response, "raise_for_status")
        saved_paths = service._get_designs(order_with_artwork_id)

        assert len(saved_paths) == 2
        spy_get.assert_called_once_with(url="/api/webtoprint/ARTWORK001/")
        spy_raise.assert_called_once()

    def test_get_designs_renames_files_with_order_id(
        self, service, mock_client, order_with_artwork_id, tmp_path
    ):
        """Test that extracted files are renamed with order ID."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        saved_paths = service._get_designs(order_with_artwork_id)

        # Check that file was saved with order ID prefix
        assert len(saved_paths) == 1
        assert "S12345_" in str(saved_paths[0])

    def test_get_designs_returns_empty_list_for_no_artwork_id(self, service, mock_client, mocker):
        """Test that no designs are downloaded if line items have no artwork ID."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.artwork_id = None

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(12345)

        spy = mocker.spy(mock_client, "get")
        saved_paths = service._get_designs(order)

        assert saved_paths == []
        spy.assert_not_called()

    def test_get_designs_sets_design_on_line_item(
        self, service, mock_client, order_with_artwork_id, mocker
    ):
        """Test that design is set on line item."""
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("design.pdf", "design content")
        zip_buffer.seek(0)

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = zip_buffer.getvalue()
        mock_client.get.return_value = mock_response

        spy = mocker.spy(order_with_artwork_id.line_items[0], "set_design")
        service._get_designs(order_with_artwork_id)

        spy.assert_called_once()
        call_kwargs = spy.call_args[1]
        assert "url" in call_kwargs
        assert "https://spectrum.example.com/api/webtoprint/ARTWORK001/" in call_kwargs["url"]
        assert "paths" in call_kwargs

    def test_get_designs_raises_on_http_error(self, service, mock_client, order_with_artwork_id):
        """Test that HTTP errors are raised."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            service._get_designs(order_with_artwork_id)


class TestSpectrumArtworkServiceGetPlacements:
    """Tests for _get_placements method."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked httpx.Client."""
        mock = Mock(spec=httpx.Client)
        mock.base_url = "https://spectrum.example.com"
        return mock

    @pytest.fixture
    def service(self, mock_client, tmp_path):
        """Provide a SpectrumArtworkService instance."""
        service = SpectrumArtworkService(engine=mock_client, digitals_dir=tmp_path)
        service._client = "CLIENT123"
        return service

    @pytest.fixture
    def order_with_artwork_id(self, mocker):
        """Provide an Order with line items that have artwork IDs."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.artwork_id = "ARTWORK001"
        line_item.product_id = "PROD001"
        line_item.quantity = 100

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-123",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(123)
        return order

    def test_get_placements_downloads_pdf(
        self, service, mock_client, order_with_artwork_id, tmp_path, mocker
    ):
        """Test that placement PDFs are downloaded."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.content = b"PDF content"
        mock_client.get.return_value = mock_response

        spy_get = mocker.spy(mock_client, "get")
        spy_raise = mocker.spy(mock_response, "raise_for_status")
        saved_paths = service._get_placements(order_with_artwork_id)

        assert len(saved_paths) == 1
        spy_get.assert_called_once_with(url="/CLIENT123/specification/ARTWORK001/pdf/")
        spy_raise.assert_called_once()

    def test_get_placements_saves_pdf_with_correct_name(
        self, service, mock_client, order_with_artwork_id, tmp_path
    ):
        """Test that PDF is saved with correct filename."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.content = b"PDF content"
        mock_client.get.return_value = mock_response

        saved_paths = service._get_placements(order_with_artwork_id)

        assert len(saved_paths) == 1
        assert "S00123_ARTWORK001_placement.pdf" in str(saved_paths[0])

    def test_get_placements_returns_empty_list_for_no_artwork_id(
        self, service, mock_client, mocker
    ):
        """Test that no placements are downloaded if line items have no artwork ID."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.artwork_id = None

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(12345)

        spy = mocker.spy(mock_client, "get")
        saved_paths = service._get_placements(order)

        assert saved_paths == []
        spy.assert_not_called()

    def test_get_placements_sets_placement_on_line_item(
        self, service, mock_client, order_with_artwork_id, mocker
    ):
        """Test that placement is set on line item."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.content = b"PDF content"
        mock_client.get.return_value = mock_response

        spy = mocker.spy(order_with_artwork_id.line_items[0], "set_placement")
        service._get_placements(order_with_artwork_id)

        spy.assert_called_once()
        call_kwargs = spy.call_args[1]
        assert "url" in call_kwargs
        assert (
            "https://spectrum.example.com/CLIENT123/specification/ARTWORK001/pdf/"
            in call_kwargs["url"]
        )
        assert "path" in call_kwargs

    def test_get_placements_raises_on_http_error(
        self, service, mock_client, order_with_artwork_id, mocker
    ):
        """Test that HTTP errors are raised."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            service._get_placements(order_with_artwork_id)

    def test_get_placements_multiple_line_items(self, service, mock_client, mocker):
        """Test that placements are downloaded for multiple line items."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item1 = mocker.Mock(spec=LineItem)
        line_item1.artwork_id = "ARTWORK001"
        line_item2 = mocker.Mock(spec=LineItem)
        line_item2.artwork_id = "ARTWORK002"

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item1, line_item2],
        )
        order.set_id(12345)

        mock_response = Mock(spec=httpx.Response)
        mock_response.content = b"PDF content"
        mock_client.get.return_value = mock_response

        spy_get = mocker.spy(mock_client, "get")
        saved_paths = service._get_placements(order)

        assert len(saved_paths) == 2
        assert spy_get.call_count == 2


class TestSpectrumArtworkServiceGetArtwork:
    """Tests for get_artwork method."""

    @pytest.fixture
    def mock_client(self):
        """Provide a mocked httpx.Client."""
        mock = Mock(spec=httpx.Client)
        mock.base_url = "https://spectrum.example.com"
        return mock

    @pytest.fixture
    def service(self, mock_client, tmp_path):
        """Provide a SpectrumArtworkService instance."""
        service = SpectrumArtworkService(engine=mock_client, digitals_dir=tmp_path)
        service._client = "CLIENT123"
        return service

    @pytest.fixture
    def order_with_artwork_id(self, mocker):
        """Provide an Order with line items that have artwork IDs."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.artwork_id = "ARTWORK001"
        line_item.product_id = "PROD001"
        line_item.quantity = 100

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(12345)
        return order

    def test_get_artwork_combines_designs_and_placements(
        self, service, mocker, order_with_artwork_id
    ):
        """Test that get_artwork combines designs and placements."""
        design_paths = [Path("/tmp/design1.pdf")]
        placement_paths = [Path("/tmp/placement1.pdf")]

        mocker.patch.object(service, "_get_designs", return_value=design_paths)
        mocker.patch.object(service, "_get_placements", return_value=placement_paths)

        result = service.get_artwork(order_with_artwork_id)

        assert result == design_paths + placement_paths

    def test_get_artwork_calls_both_methods(self, service, mocker, order_with_artwork_id):
        """Test that get_artwork calls both _get_designs and _get_placements."""
        mocked_get_designs = mocker.patch.object(service, "_get_designs", return_value=[])
        mocked_get_placements = mocker.patch.object(service, "_get_placements", return_value=[])
        service.get_artwork(order_with_artwork_id)

        mocked_get_designs.assert_called_once_with(order_with_artwork_id)
        mocked_get_placements.assert_called_once_with(order_with_artwork_id)

    def test_get_artwork_returns_empty_list_for_no_artwork_id(self, service, mocker):
        """Test that empty list is returned if no artwork IDs."""
        ship_to = mocker.Mock(spec=ShipTo)
        line_item = mocker.Mock(spec=LineItem)
        line_item.artwork_id = None

        order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="Harman",
            pricelist_id=50,
            remote_order_id="HA-EM-12345",
            shipment_type="standard",
            ship_to=ship_to,
            line_items=[line_item],
        )
        order.set_id(12345)

        result = service.get_artwork(order)

        assert result == []
