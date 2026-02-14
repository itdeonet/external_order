"""Unit tests for the LineItem domain model."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.domain.line_item import LineItem


@pytest.fixture
def valid_line_item_data():
    """Provide valid LineItem initialization data."""
    return {
        "product_id": "PROD-123",
        "quantity": 5,
    }


@pytest.fixture
def line_item(valid_line_item_data):
    """Create a basic LineItem instance for testing."""
    return LineItem(**valid_line_item_data)


@pytest.fixture
def mock_file_path(mocker):
    """Create a mocked Path object that is_file() returns True."""
    mock_path = MagicMock(spec=Path)
    mock_path.is_file.return_value = True
    return mock_path


class TestLineItemInitialization:
    """Test cases for LineItem initialization and post_init validation."""

    def test_line_item_creation_with_defaults(self, valid_line_item_data):
        """Test that LineItem is created with auto-generated ID."""
        item = LineItem(**valid_line_item_data)

        assert item.product_id == "PROD-123"
        assert item.quantity == 5
        assert item.artwork_id == ""
        assert item.design_url == ""
        assert item.design_paths == []
        assert item.placement_url == ""
        assert item.placement_path == Path("")
        # Verify ID is generated as UUID
        assert isinstance(item.id, str)
        assert len(item.id) > 0

    def test_line_item_creation_with_custom_id(self, valid_line_item_data):
        """Test that LineItem can be created with a custom ID."""
        custom_id = "custom-id-123"
        item = LineItem(id=custom_id, **valid_line_item_data)

        assert item.id == custom_id

    def test_line_item_id_is_trimmed(self):
        """Test that LineItem ID is trimmed of whitespace."""
        item = LineItem(id="  custom-id-123  ", product_id="PROD-123", quantity=5)

        assert item.id == "custom-id-123"

    def test_line_item_product_id_is_trimmed(self):
        """Test that product_id is trimmed of whitespace."""
        item = LineItem(product_id="  PROD-123  ", quantity=5)

        assert item.product_id == "PROD-123"

    def test_line_item_artwork_id_is_trimmed(self):
        """Test that artwork_id is trimmed of whitespace."""
        item = LineItem(product_id="PROD-123", quantity=5, artwork_id="  ART-456  ")

        assert item.artwork_id == "ART-456"

    def test_line_item_invalid_empty_id(self, valid_line_item_data):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            LineItem(id="", **valid_line_item_data)

    def test_line_item_invalid_whitespace_only_id(self, valid_line_item_data):
        """Test that whitespace-only ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            LineItem(id="   ", **valid_line_item_data)

    def test_line_item_invalid_non_string_id(self, valid_line_item_data):
        """Test that non-string ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            LineItem(id=123, **valid_line_item_data)  # type: ignore

    def test_line_item_invalid_empty_product_id(self):
        """Test that empty product_id raises ValueError."""
        with pytest.raises(ValueError, match="Product ID must be a non-empty string"):
            LineItem(product_id="", quantity=5)

    def test_line_item_invalid_whitespace_only_product_id(self):
        """Test that whitespace-only product_id raises ValueError."""
        with pytest.raises(ValueError, match="Product ID must be a non-empty string"):
            LineItem(product_id="   ", quantity=5)

    def test_line_item_invalid_non_string_product_id(self):
        """Test that non-string product_id raises ValueError."""
        with pytest.raises(ValueError, match="Product ID must be a non-empty string"):
            LineItem(product_id=123, quantity=5)  # type: ignore

    def test_line_item_invalid_non_integer_quantity(self, valid_line_item_data):
        """Test that non-integer quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(
                quantity="5",  # type: ignore
                **{k: v for k, v in valid_line_item_data.items() if k != "quantity"},
            )

    def test_line_item_invalid_zero_quantity(self, valid_line_item_data):
        """Test that zero quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(
                quantity=0,
                **{k: v for k, v in valid_line_item_data.items() if k != "quantity"},
            )

    def test_line_item_invalid_negative_quantity(self, valid_line_item_data):
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(
                quantity=-5,
                **{k: v for k, v in valid_line_item_data.items() if k != "quantity"},
            )

    def test_line_item_empty_artwork_id_remains_empty(self, valid_line_item_data):
        """Test that empty artwork_id stays empty."""
        item = LineItem(artwork_id="", **valid_line_item_data)

        assert item.artwork_id == ""

    def test_line_item_is_frozen(self, line_item):
        """Test that LineItem is frozen (immutable)."""
        with pytest.raises(AttributeError):
            line_item.product_id = "NEW-PROD"


class TestLineItemSetId:
    """Test cases for the set_id method."""

    def test_set_id_valid(self, line_item):
        """Test setting a valid ID."""
        new_id = "new-id-456"
        line_item.set_id(new_id)

        assert line_item.id == new_id

    def test_set_id_with_whitespace(self, line_item):
        """Test that set_id trims whitespace."""
        line_item.set_id("  new-id-456  ")

        assert line_item.id == "new-id-456"

    def test_set_id_empty_raises_error(self, line_item):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            line_item.set_id("")

    def test_set_id_whitespace_only_raises_error(self, line_item):
        """Test that whitespace-only ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            line_item.set_id("   ")

    def test_set_id_non_string_raises_error(self, line_item):
        """Test that non-string ID raises ValueError."""
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            line_item.set_id(123)


class TestLineItemSetArtworkId:
    """Test cases for the set_artwork_id method."""

    def test_set_artwork_id_valid(self, line_item):
        """Test setting a valid artwork ID."""
        artwork_id = "ART-789"
        line_item.set_artwork_id(artwork_id)

        assert line_item.artwork_id == artwork_id

    def test_set_artwork_id_with_whitespace(self, line_item):
        """Test that set_artwork_id trims whitespace."""
        line_item.set_artwork_id("  ART-789  ")

        assert line_item.artwork_id == "ART-789"

    def test_set_artwork_id_empty_raises_error(self, line_item):
        """Test that empty artwork ID raises ValueError."""
        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            line_item.set_artwork_id("")

    def test_set_artwork_id_whitespace_only_raises_error(self, line_item):
        """Test that whitespace-only artwork ID raises ValueError."""
        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            line_item.set_artwork_id("   ")

    def test_set_artwork_id_non_string_raises_error(self, line_item):
        """Test that non-string artwork ID raises ValueError."""
        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            line_item.set_artwork_id(123)


class TestLineItemSetDesign:
    """Test cases for the set_design method."""

    def test_set_design_valid(self, line_item, mock_file_path):
        """Test setting valid design URL and paths."""
        design_url = "https://example.com/design.png"
        paths = [mock_file_path]

        line_item.set_design(design_url, paths)

        assert line_item.design_url == design_url
        assert line_item.design_paths == paths

    def test_set_design_url_with_whitespace(self, line_item, mock_file_path):
        """Test that design URL is trimmed of whitespace."""
        design_url = "  https://example.com/design.png  "
        paths = [mock_file_path]

        line_item.set_design(design_url, paths)

        assert line_item.design_url == "https://example.com/design.png"

    def test_set_design_multiple_paths(self, line_item, mocker):
        """Test setting design with multiple file paths."""
        design_url = "https://example.com/design.png"
        mock_path1 = MagicMock(spec=Path)
        mock_path1.is_file.return_value = True
        mock_path2 = MagicMock(spec=Path)
        mock_path2.is_file.return_value = True
        paths = [mock_path1, mock_path2]

        line_item.set_design(design_url, paths)

        assert line_item.design_url == design_url
        assert len(line_item.design_paths) == 2

    def test_set_design_empty_url_raises_error(self, line_item, mock_file_path):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="Design URL must be a non-empty string"):
            line_item.set_design("", [mock_file_path])

    def test_set_design_whitespace_only_url_raises_error(self, line_item, mock_file_path):
        """Test that whitespace-only URL raises ValueError."""
        with pytest.raises(ValueError, match="Design URL must be a non-empty string"):
            line_item.set_design("   ", [mock_file_path])

    def test_set_design_non_string_url_raises_error(self, line_item, mock_file_path):
        """Test that non-string URL raises ValueError."""
        with pytest.raises(ValueError, match="Design URL must be a non-empty string"):
            line_item.set_design(123, [mock_file_path])

    def test_set_design_non_list_paths_raises_error(self, line_item):
        """Test that non-list paths raises ValueError."""
        design_url = "https://example.com/design.png"
        with pytest.raises(ValueError, match="Design paths must be a list of valid file paths"):
            line_item.set_design(design_url, "not a list")

    def test_set_design_non_path_objects_raises_error(self, line_item):
        """Test that non-Path objects in list raises ValueError."""
        design_url = "https://example.com/design.png"
        with pytest.raises(ValueError, match="Design paths must be a list of valid file paths"):
            line_item.set_design(design_url, ["not a path"])

    def test_set_design_non_existent_file_raises_error(self, line_item, mocker):
        """Test that non-existent file path raises ValueError."""
        design_url = "https://example.com/design.png"
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = False

        with pytest.raises(ValueError, match="Design paths must be a list of valid file paths"):
            line_item.set_design(design_url, [mock_path])


class TestLineItemSetPlacement:
    """Test cases for the set_placement method."""

    def test_set_placement_valid(self, line_item, mock_file_path):
        """Test setting valid placement URL and path."""
        placement_url = "https://example.com/placement.png"

        line_item.set_placement(placement_url, mock_file_path)

        assert line_item.placement_url == placement_url
        assert line_item.placement_path == mock_file_path

    def test_set_placement_url_with_whitespace(self, line_item, mock_file_path):
        """Test that placement URL is trimmed of whitespace."""
        placement_url = "  https://example.com/placement.png  "

        line_item.set_placement(placement_url, mock_file_path)

        assert line_item.placement_url == "https://example.com/placement.png"

    def test_set_placement_empty_url_raises_error(self, line_item, mock_file_path):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="Placement URL must be a non-empty string"):
            line_item.set_placement("", mock_file_path)

    def test_set_placement_whitespace_only_url_raises_error(self, line_item, mock_file_path):
        """Test that whitespace-only URL raises ValueError."""
        with pytest.raises(ValueError, match="Placement URL must be a non-empty string"):
            line_item.set_placement("   ", mock_file_path)

    def test_set_placement_non_string_url_raises_error(self, line_item, mock_file_path):
        """Test that non-string URL raises ValueError."""
        with pytest.raises(ValueError, match="Placement URL must be a non-empty string"):
            line_item.set_placement(123, mock_file_path)

    def test_set_placement_non_path_object_raises_error(self, line_item):
        """Test that non-Path object raises ValueError."""
        placement_url = "https://example.com/placement.png"
        with pytest.raises(ValueError, match="Placement path must be a valid file path"):
            line_item.set_placement(placement_url, "not a path")

    def test_set_placement_non_existent_file_raises_error(self, line_item):
        """Test that non-existent file path raises ValueError."""
        placement_url = "https://example.com/placement.png"
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = False

        with pytest.raises(ValueError, match="Placement path must be a valid file path"):
            line_item.set_placement(placement_url, mock_path)


class TestLineItemHasArtwork:
    """Test cases for the has_artwork method."""

    def test_has_artwork_false_by_default(self, line_item):
        """Test that has_artwork returns False for newly created item."""
        assert line_item.has_artwork() is False

    def test_has_artwork_false_with_only_artwork_id(self, line_item):
        """Test that has_artwork is False with only artwork_id set."""
        line_item.set_artwork_id("ART-123")

        assert line_item.has_artwork() is False

    def test_has_artwork_false_missing_design_url(self, line_item, mock_file_path):
        """Test that has_artwork is False when design_url is missing."""
        line_item.set_artwork_id("ART-123")
        line_item.set_design("https://example.com/design.png", [mock_file_path])
        line_item.set_placement("https://example.com/placement.png", mock_file_path)
        # Manually set design_url to empty to test the condition
        object.__setattr__(line_item, "design_url", "")

        assert line_item.has_artwork() is False

    def test_has_artwork_false_missing_design_paths(self, line_item, mock_file_path):
        """Test that has_artwork is False when design_paths is empty."""
        line_item.set_artwork_id("ART-123")
        line_item.set_design("https://example.com/design.png", [mock_file_path])
        line_item.set_placement("https://example.com/placement.png", mock_file_path)
        # Manually set design_paths to empty to test the condition
        object.__setattr__(line_item, "design_paths", [])

        assert line_item.has_artwork() is False

    def test_has_artwork_false_missing_placement_url(self, line_item, mock_file_path):
        """Test that has_artwork is False when placement_url is missing."""
        line_item.set_artwork_id("ART-123")
        line_item.set_design("https://example.com/design.png", [mock_file_path])
        line_item.set_placement("https://example.com/placement.png", mock_file_path)
        # Manually set placement_url to empty to test the condition
        object.__setattr__(line_item, "placement_url", "")

        assert line_item.has_artwork() is False

    def test_has_artwork_true_all_fields_set(self, line_item, mock_file_path):
        """Test that has_artwork returns True when all artwork fields are set."""
        line_item.set_artwork_id("ART-123")
        line_item.set_design("https://example.com/design.png", [mock_file_path])
        line_item.set_placement("https://example.com/placement.png", mock_file_path)

        assert line_item.has_artwork() is True

    def test_has_artwork_false_missing_artwork_id(self, line_item, mock_file_path):
        """Test that has_artwork is False without artwork_id."""
        # Skip setting artwork_id
        line_item.set_design("https://example.com/design.png", [mock_file_path])
        line_item.set_placement("https://example.com/placement.png", mock_file_path)

        assert line_item.has_artwork() is False
