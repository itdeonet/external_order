"""Unit tests for the PreProductionService."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from src.domain import Artwork, LineItem, Order, ShipTo
from src.services.pre_production_service import PreProductionService


@pytest.fixture
def temp_pre_production_dir():
    """Provide a temporary pre_production directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


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
def sample_order(sample_ship_to, tmp_path):
    """Provide a sample Order with a placeholder line item."""
    # Create a placeholder line item (will be replaced in tests)
    placeholder_line_item = LineItem(
        line_id="PLACEHOLDER",
        product_code="PLACEHOLDER",
        quantity=1,
    )

    order = Order(
        administration_id=1,
        customer_id=100,
        order_provider="TEST_PROVIDER",
        pricelist_id=1,
        remote_order_id="ORD-12345",
        shipment_type="STANDARD",
        description="Test order",
        ship_to=sample_ship_to,
        line_items=[placeholder_line_item],
    )
    return order


class TestPreProductionServiceInitialization:
    """Tests for PreProductionService initialization."""

    def test_pre_production_service_initializes_with_pre_production_data(self, tmp_path):
        """Test that PreProductionService loads pre_production data from file."""
        # Create a temporary pre_production data file
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text('{"PRODUCT_001": {"batch_size": 10, "directory": "output"}}')

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            service = PreProductionService()

            assert service.pre_production_data == {
                "PRODUCT_001": {"batch_size": 10, "directory": "output"}
            }

    def test_pre_production_service_handles_empty_pre_production_data(self, tmp_path):
        """Test that PreProductionService handles empty pre_production data."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            service = PreProductionService()

            assert service.pre_production_data == {}

    def test_pre_production_service_is_frozen(self, tmp_path):
        """Test that PreProductionService is frozen (immutable)."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            service = PreProductionService()

            with pytest.raises(AttributeError):
                service.pre_production_data = {}  # type: ignore


class TestCreateBatchPdf:
    """Tests for create_batch_pdf method."""

    def test_create_batch_pdf_returns_list_of_paths(self, sample_ship_to, tmp_path):
        """Test that create_batch_pdf returns a list of Path objects."""
        # Create mock design and placement files
        design_file = tmp_path / "design_upper.pdf"
        placement_file = tmp_path / "placement.pdf"
        design_file.touch()
        placement_file.touch()

        # Create artwork
        artwork = Artwork(
            artwork_id="ART001",
            artwork_line_id="LINE001",
            design_url="https://example.com/design.pdf",
            design_paths=[design_file],
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_file,
        )

        # Create line item with artwork
        line_item = LineItem(
            line_id="LINE001",
            product_code="PRODUCT_001",
            quantity=5,
            artwork=artwork,
        )

        sample_order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="TEST_PROVIDER",
            pricelist_id=1,
            remote_order_id="ORD-12345",
            shipment_type="STANDARD",
            description="Test order",
            ship_to=sample_ship_to,
            line_items=[line_item],
        )

        # Create pre_production data
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text(
            '{"PRODUCT_001": {"batch_size": 5, "directory_upper": "upper", '
            '"directory_lower": "lower", "directory": "default"}}'
        )

        # Mock pymupdf
        mock_pixmap = MagicMock()
        mock_pixmap.colorspace.name = "DeviceRGB"
        mock_pixmap.width = 100
        mock_pixmap.height = 100

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path
            mock_output_dir = tmp_path / "output"
            mock_output_dir.mkdir()

            with patch("src.services.pre_production_service.pymupdf") as mock_pymupdf:
                mock_pymupdf.Pixmap.return_value = mock_pixmap
                mock_pymupdf.csRGB.name = "DeviceRGB"
                mock_doc = MagicMock()
                mock_page = MagicMock()
                mock_doc.new_page.return_value = mock_page
                mock_pymupdf.open.return_value = mock_doc
                mock_pymupdf.Rect = lambda *args: MagicMock()

                service = PreProductionService()
                result = service.create_batch_pdf(sample_order)

                assert isinstance(result, list)
                assert all(isinstance(p, Path) for p in result)

    def test_create_batch_pdf_skips_line_items_without_artwork(self, sample_ship_to, tmp_path):
        """Test that create_batch_pdf skips line items without artwork."""
        # Create line item without artwork
        line_item = LineItem(
            line_id="LINE001",
            product_code="PRODUCT_001",
            quantity=5,
            artwork=None,
        )

        sample_order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="TEST_PROVIDER",
            pricelist_id=1,
            remote_order_id="ORD-12345",
            shipment_type="STANDARD",
            description="Test order",
            ship_to=sample_ship_to,
            line_items=[line_item],
        )

        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text('{"PRODUCT_001": {"batch_size": 5}}')

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            service = PreProductionService()
            result = service.create_batch_pdf(sample_order)

            assert result == []

    def test_create_batch_pdf_handles_color_space_conversion(self, sample_ship_to, tmp_path):
        """Test that create_batch_pdf converts non-RGB color spaces."""
        design_file = tmp_path / "design.pdf"
        placement_file = tmp_path / "placement.pdf"
        design_file.touch()
        placement_file.touch()

        artwork = Artwork(
            artwork_id="ART001",
            artwork_line_id="LINE001",
            design_url="https://example.com/design.pdf",
            design_paths=[design_file],
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_file,
        )

        line_item = LineItem(
            line_id="LINE001",
            product_code="PRODUCT_001",
            quantity=1,
            artwork=artwork,
        )

        sample_order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="TEST_PROVIDER",
            pricelist_id=1,
            remote_order_id="ORD-12345",
            shipment_type="STANDARD",
            description="Test order",
            ship_to=sample_ship_to,
            line_items=[line_item],
        )

        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text('{"PRODUCT_001": {"batch_size": 1, "directory": "output"}}')

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock pymupdf with CMYK color space
        mock_pixmap = MagicMock()
        mock_pixmap.colorspace.name = "DeviceCMYK"
        mock_pixmap.width = 100
        mock_pixmap.height = 100

        mock_converted_pixmap = MagicMock()
        mock_converted_pixmap.width = 100
        mock_converted_pixmap.height = 100

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            with patch("src.services.pre_production_service.pymupdf") as mock_pymupdf:
                mock_pymupdf.Pixmap.side_effect = [
                    mock_pixmap,  # First call returns CMYK pixmap
                    mock_converted_pixmap,  # Second call returns converted RGB pixmap
                ]
                mock_pymupdf.csRGB.name = "DeviceRGB"

                mock_doc = MagicMock()
                mock_page = MagicMock()
                mock_doc.new_page.return_value = mock_page
                mock_pymupdf.open.return_value = mock_doc
                mock_pymupdf.Rect = lambda *args: MagicMock()

                service = PreProductionService()
                service.create_batch_pdf(sample_order)

                # Verify color space conversion was called
                assert mock_pymupdf.Pixmap.call_count >= 2
                mock_doc.save.assert_called_once()

    def test_create_batch_pdf_with_multiple_line_items(self, sample_ship_to, tmp_path):
        """Test create_batch_pdf with multiple line items."""
        # Create design and placement files
        design_file1 = tmp_path / "design1_upper.pdf"
        design_file2 = tmp_path / "design2_lower.pdf"
        placement_file1 = tmp_path / "placement1.pdf"
        placement_file2 = tmp_path / "placement2.pdf"
        design_file1.touch()
        design_file2.touch()
        placement_file1.touch()
        placement_file2.touch()

        # Create artworks
        artwork1 = Artwork(
            artwork_id="ART001",
            artwork_line_id="LINE001",
            design_url="https://example.com/design1.pdf",
            design_paths=[design_file1],
            placement_url="https://example.com/placement1.pdf",
            placement_path=placement_file1,
        )

        artwork2 = Artwork(
            artwork_id="ART002",
            artwork_line_id="LINE002",
            design_url="https://example.com/design2.pdf",
            design_paths=[design_file2],
            placement_url="https://example.com/placement2.pdf",
            placement_path=placement_file2,
        )

        # Create line items
        line_item1 = LineItem(
            line_id="LINE001",
            product_code="PRODUCT_001",
            quantity=10,
            artwork=artwork1,
        )
        line_item2 = LineItem(
            line_id="LINE002",
            product_code="PRODUCT_002",
            quantity=5,
            artwork=artwork2,
        )

        sample_order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="TEST_PROVIDER",
            pricelist_id=1,
            remote_order_id="ORD-12345",
            shipment_type="STANDARD",
            description="Test order",
            ship_to=sample_ship_to,
            line_items=[line_item1, line_item2],
        )

        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text(
            '{"PRODUCT_001": {"batch_size": 5, "directory_upper": "upper", "directory_lower": "lower"},'
            '"PRODUCT_002": {"batch_size": 5, "directory_upper": "upper", "directory_lower": "lower"}}'
        )

        # Create output directories
        (tmp_path / "upper").mkdir()
        (tmp_path / "lower").mkdir()

        mock_pixmap = MagicMock()
        mock_pixmap.colorspace.name = "DeviceRGB"
        mock_pixmap.width = 100
        mock_pixmap.height = 100

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            with patch("src.services.pre_production_service.pymupdf") as mock_pymupdf:
                mock_pymupdf.Pixmap.return_value = mock_pixmap
                mock_pymupdf.csRGB.name = "DeviceRGB"
                mock_doc = MagicMock()
                mock_page = MagicMock()
                mock_doc.new_page.return_value = mock_page
                mock_pymupdf.open.return_value = mock_doc
                mock_pymupdf.Rect = lambda *args: MagicMock()

                service = PreProductionService()
                result = service.create_batch_pdf(sample_order)

                # Should have created PDFs for both line items
                assert len(result) >= 2
                assert all(isinstance(p, Path) for p in result)

    def test_create_batch_pdf_batch_size_calculation(self, sample_ship_to, tmp_path):
        """Test that batches are correctly sized based on batch_size."""
        design_file = tmp_path / "design.pdf"
        placement_file = tmp_path / "placement.pdf"
        design_file.touch()
        placement_file.touch()

        artwork = Artwork(
            artwork_id="ART001",
            artwork_line_id="LINE001",
            design_url="https://example.com/design.pdf",
            design_paths=[design_file],
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_file,
        )

        # Create line item with quantity 11, batch_size 5
        # Should create 3 batches: (5, 5, 1)
        line_item = LineItem(
            line_id="LINE001",
            product_code="PRODUCT_001",
            quantity=11,
            artwork=artwork,
        )

        sample_order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="TEST_PROVIDER",
            pricelist_id=1,
            remote_order_id="ORD-12345",
            shipment_type="STANDARD",
            description="Test order",
            ship_to=sample_ship_to,
            line_items=[line_item],
        )

        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text('{"PRODUCT_001": {"batch_size": 5, "directory": "output"}}')

        (tmp_path / "output").mkdir()

        mock_pixmap = MagicMock()
        mock_pixmap.colorspace.name = "DeviceRGB"
        mock_pixmap.width = 100
        mock_pixmap.height = 100

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            with patch("src.services.pre_production_service.pymupdf") as mock_pymupdf:
                mock_pymupdf.Pixmap.return_value = mock_pixmap
                mock_pymupdf.csRGB.name = "DeviceRGB"
                mock_doc = MagicMock()
                mock_page = MagicMock()
                mock_doc.new_page.return_value = mock_page
                mock_pymupdf.open.return_value = mock_doc
                mock_pymupdf.Rect = lambda *args: MagicMock()

                service = PreProductionService()
                result = service.create_batch_pdf(sample_order)

                # Should create 3 PDF files (batches)
                assert len(result) == 3

    def test_create_batch_pdf_documents_are_closed(self, sample_ship_to, tmp_path):
        """Test that PDF documents are properly closed after saving."""
        design_file = tmp_path / "design.pdf"
        placement_file = tmp_path / "placement.pdf"
        design_file.touch()
        placement_file.touch()

        artwork = Artwork(
            artwork_id="ART001",
            artwork_line_id="LINE001",
            design_url="https://example.com/design.pdf",
            design_paths=[design_file],
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_file,
        )

        line_item = LineItem(
            line_id="LINE001",
            product_code="PRODUCT_001",
            quantity=5,
            artwork=artwork,
        )

        sample_order = Order(
            administration_id=1,
            customer_id=100,
            order_provider="TEST_PROVIDER",
            pricelist_id=1,
            remote_order_id="ORD-12345",
            shipment_type="STANDARD",
            description="Test order",
            ship_to=sample_ship_to,
            line_items=[line_item],
        )

        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text('{"PRODUCT_001": {"batch_size": 5, "directory": "output"}}')

        (tmp_path / "output").mkdir()

        mock_pixmap = MagicMock()
        mock_pixmap.colorspace.name = "DeviceRGB"
        mock_pixmap.width = 100
        mock_pixmap.height = 100

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            with patch("src.services.pre_production_service.pymupdf") as mock_pymupdf:
                mock_pymupdf.Pixmap.return_value = mock_pixmap
                mock_pymupdf.csRGB.name = "DeviceRGB"
                mock_doc = MagicMock()
                mock_page = MagicMock()
                mock_doc.new_page.return_value = mock_page
                mock_pymupdf.open.return_value = mock_doc
                mock_pymupdf.Rect = lambda *args: MagicMock()

                service = PreProductionService()
                service.create_batch_pdf(sample_order)

                # Verify doc.close() was called
                mock_doc.close.assert_called()


class TestGetBatchPath:
    """Tests for _get_batch_path method."""

    def test_get_batch_path_for_upper_design(self, tmp_path):
        """Test _get_batch_path returns correct path for upper design."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            service = PreProductionService()

            design_path = tmp_path / "design_upper.pdf"
            product_data = {
                "directory_upper": "upper_output",
                "directory_lower": "lower_output",
                "directory": "default_output",
            }

            result = service._get_batch_path(design_path, product_data, "1234", 1)

            assert result.parent.name == "upper_output"
            assert result.name == "_1234_1_upper.pdf"
            assert result.parent.exists()

    def test_get_batch_path_for_lower_design(self, tmp_path):
        """Test _get_batch_path returns correct path for lower design."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            service = PreProductionService()

            design_path = tmp_path / "design_lower.pdf"
            product_data = {
                "directory_upper": "upper_output",
                "directory_lower": "lower_output",
                "directory": "default_output",
            }

            result = service._get_batch_path(design_path, product_data, "1234", 2)

            assert result.parent.name == "lower_output"
            assert result.name == "_1234_2_lower.pdf"

    def test_get_batch_path_for_default_design(self, tmp_path):
        """Test _get_batch_path returns correct path for default design."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            service = PreProductionService()

            design_path = tmp_path / "design.pdf"
            product_data = {
                "directory_upper": "upper_output",
                "directory_lower": "lower_output",
                "directory": "default_output",
            }

            result = service._get_batch_path(design_path, product_data, "5678", 1)

            assert result.parent.name == "default_output"
            assert result.name == "_5678_1.pdf"

    def test_get_batch_path_creates_directories(self, tmp_path):
        """Test that _get_batch_path creates the output directory if it doesn't exist."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            service = PreProductionService()

            design_path = tmp_path / "design.pdf"
            product_data = {"directory": "nested/output/path"}

            result = service._get_batch_path(design_path, product_data, "1234", 1)

            assert result.parent.exists()
            assert result.parent == tmp_path / "nested/output/path"

    def test_get_batch_path_handles_case_insensitive_upper(self, tmp_path):
        """Test that _get_batch_path handles case-insensitive 'UPPER' in filename."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            service = PreProductionService()

            design_path = tmp_path / "design_UPPER.pdf"
            product_data = {"directory_upper": "upper_output"}

            result = service._get_batch_path(design_path, product_data, "1234", 1)

            assert result.parent.name == "upper_output"
            assert "_upper" in result.name

    def test_get_batch_path_partial_order_name_extraction(self, tmp_path):
        """Test that _get_batch_path correctly extracts partial order name."""
        pre_production_file = tmp_path / "pre_production_data.json"
        pre_production_file.write_text("{}")

        with patch("src.services.pre_production_service.get_config") as mock_config:
            mock_config.return_value.pre_production_data_file = pre_production_file
            mock_config.return_value.pre_production_dir = tmp_path

            service = PreProductionService()

            # Design path stem: "FOO123456_upper"
            # Last 4 chars of stem before underscore: "3456"
            design_path = tmp_path / "FOO123456_upper.pdf"
            product_data = {"directory_upper": "upper_output"}

            result = service._get_batch_path(design_path, product_data, "9999", 1)

            # The batch number should use the provided partial_order_name
            assert result.name == "_9999_1_upper.pdf"
