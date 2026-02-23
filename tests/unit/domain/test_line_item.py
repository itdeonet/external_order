"""Unit tests for the LineItem domain model."""

import uuid
from pathlib import Path

import pytest

from src.domain.artwork import Artwork
from src.domain.line_item import LineItem


@pytest.fixture
def valid_line_item_data():
    """Provide valid LineItem initialization data."""
    return {
        "remote_line_id": "RL-001",
        "product_code": "PROD-123",
        "quantity": 5,
    }


@pytest.fixture
def line_item(valid_line_item_data):
    """Create a basic LineItem instance for testing."""
    return LineItem(**valid_line_item_data)


@pytest.fixture
def mock_file_path(mocker):
    """Create a mocked Path object that is_file() returns True."""
    mock_path = mocker.Mock(spec=Path)
    mock_path.is_file.return_value = True
    return mock_path


class TestLineItemInitialization:
    """Test cases for LineItem initialization and post_init validation."""

    def test_line_item_creation_with_defaults(self, valid_line_item_data):
        """Test that LineItem is created with auto-generated ID."""
        item = LineItem(**valid_line_item_data)

        assert item.remote_line_id == "RL-001"
        assert item.product_code == "PROD-123"
        assert item.quantity == 5
        assert item.artwork is None
        # Verify ID is generated as UUID
        assert isinstance(item.id, uuid.UUID)

    def test_line_item_id_is_trimmed(self, valid_line_item_data):
        """Test that LineItem ID is trimmed of whitespace."""
        valid_line_item_data["remote_line_id"] = "  custom-id-123  "
        item = LineItem(**valid_line_item_data)

        assert item.remote_line_id == "custom-id-123"

    def test_line_item_product_code_is_trimmed(self, valid_line_item_data):
        """Test that product_code is trimmed of whitespace."""
        valid_line_item_data["product_code"] = "  PROD-123  "
        item = LineItem(**valid_line_item_data)

        assert item.product_code == "PROD-123"

    def test_line_item_artwork_is_set(self, valid_line_item_data, mocker):
        """Test that artwork is set correctly."""
        mock_artwork = mocker.Mock(spec=Artwork)
        valid_line_item_data["artwork"] = mock_artwork
        item = LineItem(**valid_line_item_data)

        assert item.artwork == mock_artwork

    def test_line_item_invalid_empty_remote_line_id(self, valid_line_item_data):
        """Test that empty ID raises ValueError."""
        valid_line_item_data["remote_line_id"] = ""
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            LineItem(**valid_line_item_data)

    def test_line_item_invalid_whitespace_only_id(self, valid_line_item_data):
        """Test that whitespace-only ID raises ValueError."""
        valid_line_item_data["remote_line_id"] = "   "
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            LineItem(**valid_line_item_data)

    def test_line_item_invalid_non_string_remote_line_id(self, valid_line_item_data):
        """Test that non-string ID raises ValueError."""
        valid_line_item_data["remote_line_id"] = 123
        with pytest.raises(ValueError, match="ID must be a non-empty string"):
            LineItem(**valid_line_item_data)  # type: ignore

    def test_line_item_invalid_empty_product_code(self, valid_line_item_data):
        """Test that empty product_code raises ValueError."""
        valid_line_item_data["product_code"] = ""
        with pytest.raises(ValueError, match="Product code must be a non-empty string"):
            LineItem(**valid_line_item_data)

    def test_line_item_invalid_whitespace_only_product_code(self, valid_line_item_data):
        """Test that whitespace-only product_code raises ValueError."""
        valid_line_item_data["product_code"] = "   "
        with pytest.raises(ValueError, match="Product code must be a non-empty string"):
            LineItem(**valid_line_item_data)

    def test_line_item_invalid_non_string_product_code(self, valid_line_item_data):
        """Test that non-string product_code raises ValueError."""
        valid_line_item_data["product_code"] = 456
        with pytest.raises(ValueError, match="Product code must be a non-empty string"):
            LineItem(**valid_line_item_data)  # type: ignore

    def test_line_item_invalid_none_product_code(self, valid_line_item_data):
        """Test that None product_code raises ValueError."""
        valid_line_item_data["product_code"] = None
        with pytest.raises(ValueError, match="Product code must be a non-empty string"):
            LineItem(**valid_line_item_data)  # type: ignore

    def test_line_item_invalid_none_remote_line_id(self, valid_line_item_data):
        """Test that None remote_line_id raises ValueError."""
        valid_line_item_data["remote_line_id"] = None
        with pytest.raises(ValueError, match="Remote line ID must be a non-empty string"):
            LineItem(**valid_line_item_data)  # type: ignore


class TestLineItemQuantityValidation:
    """Test cases for LineItem quantity field validation."""

    @pytest.fixture
    def minimal_line_item_data(self):
        """Provide minimal valid LineItem data for quantity tests."""
        return {
            "remote_line_id": "RL-001",
            "product_code": "PROD-123",
        }

    def test_quantity_required(self, minimal_line_item_data):
        """Test that quantity is required."""
        with pytest.raises(TypeError):
            LineItem(**minimal_line_item_data)

    def test_quantity_must_be_positive(self, minimal_line_item_data):
        """Test that quantity must be positive."""
        minimal_line_item_data["quantity"] = -1
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(**minimal_line_item_data)

    def test_quantity_zero_is_invalid(self, minimal_line_item_data):
        """Test that quantity of 0 is invalid."""
        minimal_line_item_data["quantity"] = 0
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(**minimal_line_item_data)

    def test_quantity_must_be_integer(self, minimal_line_item_data):
        """Test that quantity must be an integer."""
        minimal_line_item_data["quantity"] = 5.5
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(**minimal_line_item_data)  # type: ignore

    def test_quantity_must_not_be_string(self, minimal_line_item_data):
        """Test that quantity cannot be a string."""
        minimal_line_item_data["quantity"] = "5"
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(**minimal_line_item_data)  # type: ignore

    def test_quantity_must_not_be_none(self, minimal_line_item_data):
        """Test that quantity cannot be None."""
        minimal_line_item_data["quantity"] = None
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            LineItem(**minimal_line_item_data)  # type: ignore

    def test_quantity_large_positive_integer_is_valid(self, minimal_line_item_data):
        """Test that large positive integers are accepted."""
        minimal_line_item_data["quantity"] = 1000000
        item = LineItem(**minimal_line_item_data)
        assert item.quantity == 1000000

    def test_quantity_one_is_valid(self, minimal_line_item_data):
        """Test that quantity of 1 is valid."""
        minimal_line_item_data["quantity"] = 1
        item = LineItem(**minimal_line_item_data)
        assert item.quantity == 1


class TestLineItemArtworkValidation:
    """Test cases for LineItem artwork field validation."""

    @pytest.fixture
    def valid_line_item_data(self):
        """Provide valid LineItem initialization data."""
        return {
            "remote_line_id": "RL-001",
            "product_code": "PROD-123",
            "quantity": 5,
        }

    def test_artwork_none_by_default(self, valid_line_item_data):
        """Test that artwork defaults to None."""
        item = LineItem(**valid_line_item_data)
        assert item.artwork is None

    def test_artwork_must_be_artwork_instance_or_none(self, valid_line_item_data, mocker):
        """Test that artwork must be Artwork instance or None."""
        mock_artwork = mocker.Mock(spec=Artwork)
        valid_line_item_data["artwork"] = mock_artwork
        item = LineItem(**valid_line_item_data)
        assert item.artwork == mock_artwork

    def test_artwork_cannot_be_string(self, valid_line_item_data):
        """Test that artwork cannot be a string."""
        valid_line_item_data["artwork"] = "not an artwork"
        with pytest.raises(ValueError, match="Artwork must be an instance of Artwork or None"):
            LineItem(**valid_line_item_data)

    def test_artwork_cannot_be_dict(self, valid_line_item_data):
        """Test that artwork cannot be a dict."""
        valid_line_item_data["artwork"] = {}
        with pytest.raises(ValueError, match="Artwork must be an instance of Artwork or None"):
            LineItem(**valid_line_item_data)

    def test_artwork_cannot_be_integer(self, valid_line_item_data):
        """Test that artwork cannot be an integer."""
        valid_line_item_data["artwork"] = 123
        with pytest.raises(ValueError, match="Artwork must be an instance of Artwork or None"):
            LineItem(**valid_line_item_data)  # type: ignore


class TestLineItemSetArtwork:
    """Test cases for LineItem set_artwork method."""

    @pytest.fixture
    def line_item(self, valid_line_item_data):
        """Create a LineItem instance for testing."""
        return LineItem(**valid_line_item_data)

    @pytest.fixture
    def valid_line_item_data(self):
        """Provide valid LineItem data."""
        return {
            "remote_line_id": "RL-001",
            "product_code": "PROD-123",
            "quantity": 5,
        }

    def test_set_artwork_with_valid_artwork(self, line_item, mocker):
        """Test setting artwork with a valid Artwork instance."""
        mock_artwork = mocker.Mock(spec=Artwork)
        line_item.set_artwork(mock_artwork)
        assert line_item.artwork == mock_artwork

    def test_set_artwork_to_none(self, line_item):
        """Test setting artwork to None."""
        line_item.set_artwork(None)
        assert line_item.artwork is None

    def test_set_artwork_with_invalid_type(self, line_item):
        """Test that set_artwork rejects invalid artwork types."""
        with pytest.raises(ValueError, match="Artwork must be an instance of Artwork or None"):
            line_item.set_artwork("not an artwork")  # type: ignore


class TestLineItemIDGeneration:
    """Test cases for LineItem ID auto-generation."""

    @pytest.fixture
    def valid_line_item_data(self):
        """Provide valid LineItem data."""
        return {
            "remote_line_id": "RL-001",
            "product_code": "PROD-123",
            "quantity": 5,
        }

    def test_id_is_auto_generated_uuid(self, valid_line_item_data):
        """Test that id is auto-generated as UUID object."""
        item = LineItem(**valid_line_item_data)
        assert isinstance(item.id, uuid.UUID)

    def test_id_cannot_be_passed_as_parameter(self, valid_line_item_data):
        """Test that id parameter is rejected (init=False)."""
        with pytest.raises(TypeError):
            LineItem(id=uuid.uuid4(), **valid_line_item_data)  # type: ignore

    def test_id_unique_across_instances(self, valid_line_item_data):
        """Test that different instances get unique IDs."""
        item1 = LineItem(**valid_line_item_data)
        item2 = LineItem(**valid_line_item_data)
        assert item1.id != item2.id
        assert isinstance(item1.id, uuid.UUID)
        assert isinstance(item2.id, uuid.UUID)


class TestLineItemImmutability:
    """Tests for LineItem immutability (frozen dataclass)."""

    @pytest.fixture
    def line_item(self, valid_line_item_data):
        """Create a LineItem instance for testing."""
        return LineItem(**valid_line_item_data)

    @pytest.fixture
    def valid_line_item_data(self):
        """Provide valid LineItem data."""
        return {
            "remote_line_id": "RL-001",
            "product_code": "PROD-123",
            "quantity": 5,
        }

    def test_cannot_modify_remote_line_id(self, line_item):
        """Test that remote_line_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            line_item.remote_line_id = "RL-002"  # type: ignore

    def test_cannot_modify_product_code(self, line_item):
        """Test that product_code cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            line_item.product_code = "PROD-456"  # type: ignore

    def test_cannot_modify_quantity(self, line_item):
        """Test that quantity cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            line_item.quantity = 10  # type: ignore

    def test_can_modify_artwork_via_set_artwork(self, line_item, mocker):
        """Test that artwork can be modified via set_artwork method."""
        mock_artwork = mocker.Mock(spec=Artwork)
        line_item.set_artwork(mock_artwork)
        assert line_item.artwork == mock_artwork

    def test_cannot_directly_modify_artwork(self, line_item, mocker):
        """Test that artwork cannot be modified directly (use set_artwork)."""
        mock_artwork = mocker.Mock(spec=Artwork)
        with pytest.raises((AttributeError, TypeError)):
            line_item.artwork = mock_artwork  # type: ignore


class TestLineItemEquality:
    """Tests for LineItem equality comparison."""

    @pytest.fixture
    def valid_line_item_data(self):
        """Provide valid LineItem data."""
        return {
            "remote_line_id": "RL-001",
            "product_code": "PROD-123",
            "quantity": 5,
        }

    def test_same_instance_equals_itself(self, valid_line_item_data):
        """Test that a line item equals itself."""
        item = LineItem(**valid_line_item_data)
        assert item == item

    def test_different_instances_same_data_are_not_equal(self, valid_line_item_data):
        """Test that two instances with same data are not equal (different auto-generated IDs)."""
        item1 = LineItem(**valid_line_item_data)
        item2 = LineItem(**valid_line_item_data)
        # Different instances should not be equal due to different auto-generated IDs
        assert item1 != item2

    def test_different_remote_line_id_not_equal(self, valid_line_item_data):
        """Test that line items with different remote_line_ids are not equal."""
        item1 = LineItem(**valid_line_item_data)
        valid_line_item_data["remote_line_id"] = "RL-002"
        item2 = LineItem(**valid_line_item_data)
        assert item1 != item2

    def test_different_product_code_not_equal(self, valid_line_item_data):
        """Test that line items with different product_codes are not equal."""
        item1 = LineItem(**valid_line_item_data)
        valid_line_item_data["product_code"] = "PROD-456"
        item2 = LineItem(**valid_line_item_data)
        assert item1 != item2

    def test_different_quantity_not_equal(self, valid_line_item_data):
        """Test that line items with different quantities are not equal."""
        item1 = LineItem(**valid_line_item_data)
        valid_line_item_data["quantity"] = 10
        item2 = LineItem(**valid_line_item_data)
        assert item1 != item2

    def test_different_artwork_not_equal(self, valid_line_item_data, mocker):
        """Test that line items with different artwork are not equal."""
        item1 = LineItem(**valid_line_item_data)
        mock_artwork = mocker.Mock(spec=Artwork)
        valid_line_item_data["artwork"] = mock_artwork
        item2 = LineItem(**valid_line_item_data)
        assert item1 != item2


class TestLineItemRepresentation:
    """Tests for LineItem string representation."""

    @pytest.fixture
    def line_item(self, valid_line_item_data):
        """Create a LineItem instance for testing."""
        return LineItem(**valid_line_item_data)

    @pytest.fixture
    def valid_line_item_data(self):
        """Provide valid LineItem data."""
        return {
            "remote_line_id": "RL-001",
            "product_code": "PROD-123",
            "quantity": 5,
        }

    def test_repr_contains_class_name(self, line_item):
        """Test that repr contains LineItem class name."""
        repr_str = repr(line_item)
        assert "LineItem" in repr_str

    def test_repr_contains_remote_line_id(self, line_item):
        """Test that repr contains remote_line_id value."""
        repr_str = repr(line_item)
        assert "RL-001" in repr_str

    def test_repr_contains_product_code(self, line_item):
        """Test that repr contains product_code value."""
        repr_str = repr(line_item)
        assert "PROD-123" in repr_str

    def test_repr_contains_id(self, line_item):
        """Test that repr contains the auto-generated id."""
        repr_str = repr(line_item)
        assert str(line_item.id) in repr_str
