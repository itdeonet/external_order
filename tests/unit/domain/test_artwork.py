"""Unit tests for the Artwork domain class."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.domain.artwork import Artwork


class TestArtworkInstantiation:
    """Tests for basic Artwork instantiation."""

    @pytest.fixture
    def valid_design_paths(self):
        """Provide valid design paths with mocked file checks."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        return paths

    @pytest.fixture
    def valid_placement_path(self):
        """Provide valid placement path with mocked file checks."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        return mock_path

    @pytest.fixture
    def valid_artwork_data(self, valid_design_paths, valid_placement_path):
        """Provide valid Artwork initialization data."""
        return {
            "artwork_id": "ART-001",
            "line_item_id": "LI-001",
            "design_url": "https://example.com/design.pdf",
            "design_paths": valid_design_paths,
            "placement_url": "https://example.com/placement.pdf",
            "placement_path": valid_placement_path,
        }

    def test_instantiation_with_all_fields(self, valid_artwork_data):
        """Test creating an Artwork with all fields."""
        artwork = Artwork(**valid_artwork_data)

        assert isinstance(artwork.id, uuid.UUID)
        assert artwork.artwork_id == "ART-001"
        assert artwork.line_item_id == "LI-001"
        assert artwork.design_url == "https://example.com/design.pdf"
        assert artwork.design_paths == valid_artwork_data["design_paths"]
        assert artwork.placement_url == "https://example.com/placement.pdf"
        assert artwork.placement_path is valid_artwork_data["placement_path"]

    def test_id_is_auto_generated_uuid(self, valid_artwork_data):
        """Test that id is auto-generated as UUID object."""
        artwork = Artwork(**valid_artwork_data)
        assert isinstance(artwork.id, uuid.UUID)

    def test_id_cannot_be_passed_as_parameter(self, valid_artwork_data):
        """Test that id parameter is rejected (init=False)."""
        with pytest.raises(TypeError):
            Artwork(id=uuid.uuid4(), **valid_artwork_data)  # type: ignore

    def test_id_unique_across_instances(self, valid_artwork_data):
        """Test that different instances get unique IDs."""
        artwork1 = Artwork(**valid_artwork_data)
        artwork2 = Artwork(**valid_artwork_data)
        assert artwork1.id != artwork2.id
        assert isinstance(artwork1.id, uuid.UUID)
        assert isinstance(artwork2.id, uuid.UUID)

    def test_artwork_id_gets_stripped(self, valid_artwork_data):
        """Test that whitespace around artwork_id is stripped."""
        valid_artwork_data["artwork_id"] = "  ART-001  "
        artwork = Artwork(**valid_artwork_data)
        assert artwork.artwork_id == "ART-001"

    def test_line_item_id_gets_stripped(self, valid_artwork_data):
        """Test that whitespace around line_item_id is stripped."""
        valid_artwork_data["line_item_id"] = "  LI-001  "
        artwork = Artwork(**valid_artwork_data)
        assert artwork.line_item_id == "LI-001"

    def test_design_url_gets_stripped(self, valid_artwork_data):
        """Test that whitespace around design_url is stripped."""
        valid_artwork_data["design_url"] = "  https://example.com/design.pdf  "
        artwork = Artwork(**valid_artwork_data)
        assert artwork.design_url == "https://example.com/design.pdf"

    def test_placement_url_gets_stripped(self, valid_artwork_data):
        """Test that whitespace around placement_url is stripped."""
        valid_artwork_data["placement_url"] = "  https://example.com/placement.pdf  "
        artwork = Artwork(**valid_artwork_data)
        assert artwork.placement_url == "https://example.com/placement.pdf"


class TestArtworkIDValidation:
    """Tests for id field validation."""

    @pytest.fixture
    def valid_design_paths(self):
        """Provide valid design paths with mocked file checks."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        return paths

    @pytest.fixture
    def valid_placement_path(self):
        """Provide valid placement path with mocked file checks."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        return mock_path

    @pytest.fixture
    def minimal_artwork_data(self, valid_design_paths, valid_placement_path):
        """Provide minimal valid Artwork data."""
        return {
            "line_item_id": "LI-001",
            "design_url": "https://example.com/design.pdf",
            "design_paths": valid_design_paths,
            "placement_url": "https://example.com/placement.pdf",
            "placement_path": valid_placement_path,
        }

    def test_artwork_id_required(self, minimal_artwork_data):
        """Test that artwork_id is required."""
        with pytest.raises(TypeError):
            Artwork(**minimal_artwork_data)

    def test_artwork_id_empty_raises_error(self, minimal_artwork_data):
        """Test that empty artwork_id raises ValueError."""
        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            Artwork(artwork_id="", **minimal_artwork_data)

    def test_artwork_id_whitespace_only_raises_error(self, minimal_artwork_data):
        """Test that whitespace-only artwork_id raises ValueError."""
        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            Artwork(artwork_id="   ", **minimal_artwork_data)

    def test_artwork_id_not_string_raises_error(self, minimal_artwork_data):
        """Test that non-string artwork_id raises ValueError."""
        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            Artwork(artwork_id=123, **minimal_artwork_data)  # type: ignore

    def test_artwork_id_none_raises_error(self, minimal_artwork_data):
        """Test that None artwork_id raises ValueError."""
        with pytest.raises(ValueError, match="Artwork ID must be a non-empty string"):
            Artwork(artwork_id=None, **minimal_artwork_data)  # type: ignore


class TestArtworkLineItemIDValidation:
    """Tests for line_item_id field validation."""

    @pytest.fixture
    def valid_design_paths(self):
        """Provide valid design paths with mocked file checks."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        return paths

    @pytest.fixture
    def valid_placement_path(self):
        """Provide valid placement path with mocked file checks."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        return mock_path

    @pytest.fixture
    def minimal_artwork_data(self, valid_design_paths, valid_placement_path):
        """Provide minimal valid Artwork data."""
        return {
            "artwork_id": "ART-001",
            "design_url": "https://example.com/design.pdf",
            "design_paths": valid_design_paths,
            "placement_url": "https://example.com/placement.pdf",
            "placement_path": valid_placement_path,
        }

    def test_line_item_id_required(self, minimal_artwork_data):
        """Test that line_item_id is required."""
        with pytest.raises(TypeError):
            Artwork(**minimal_artwork_data)

    def test_line_item_id_empty_raises_error(self, minimal_artwork_data):
        """Test that empty line_item_id raises ValueError."""
        with pytest.raises(ValueError, match="Line item ID must be a non-empty string"):
            Artwork(line_item_id="", **minimal_artwork_data)

    def test_line_item_id_whitespace_only_raises_error(self, minimal_artwork_data):
        """Test that whitespace-only line_item_id raises ValueError."""
        with pytest.raises(ValueError, match="Line item ID must be a non-empty string"):
            Artwork(line_item_id="   ", **minimal_artwork_data)

    def test_line_item_id_not_string_raises_error(self, minimal_artwork_data):
        """Test that non-string line_item_id raises ValueError."""
        with pytest.raises(ValueError, match="Line item ID must be a non-empty string"):
            Artwork(line_item_id=456, **minimal_artwork_data)  # type: ignore

    def test_line_item_id_none_raises_error(self, minimal_artwork_data):
        """Test that None line_item_id raises ValueError."""
        with pytest.raises(ValueError, match="Line item ID must be a non-empty string"):
            Artwork(line_item_id=None, **minimal_artwork_data)  # type: ignore


class TestArtworkDesignURLValidation:
    """Tests for design_url field validation."""

    @pytest.fixture
    def valid_design_paths(self):
        """Provide valid design paths with mocked file checks."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        return paths

    @pytest.fixture
    def valid_placement_path(self):
        """Provide valid placement path with mocked file checks."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        return mock_path

    @pytest.fixture
    def minimal_artwork_data(self, valid_design_paths, valid_placement_path):
        """Provide minimal valid Artwork data."""
        return {
            "artwork_id": "ART-001",
            "line_item_id": "LI-001",
            "design_paths": valid_design_paths,
            "placement_url": "https://example.com/placement.pdf",
            "placement_path": valid_placement_path,
        }

    def test_design_url_required(self, minimal_artwork_data):
        """Test that design_url is required."""
        with pytest.raises(TypeError):
            Artwork(**minimal_artwork_data)

    def test_design_url_empty_raises_error(self, minimal_artwork_data):
        """Test that empty design_url raises ValueError."""
        with pytest.raises(ValueError, match="Design URL must be a non-empty string"):
            Artwork(design_url="", **minimal_artwork_data)

    def test_design_url_whitespace_only_raises_error(self, minimal_artwork_data):
        """Test that whitespace-only design_url raises ValueError."""
        with pytest.raises(ValueError, match="Design URL must be a non-empty string"):
            Artwork(design_url="   ", **minimal_artwork_data)

    def test_design_url_not_string_raises_error(self, minimal_artwork_data):
        """Test that non-string design_url raises ValueError."""
        with pytest.raises(ValueError, match="Design URL must be a non-empty string"):
            Artwork(design_url=789, **minimal_artwork_data)  # type: ignore

    def test_design_url_none_raises_error(self, minimal_artwork_data):
        """Test that None design_url raises ValueError."""
        with pytest.raises(ValueError, match="Design URL must be a non-empty string"):
            Artwork(design_url=None, **minimal_artwork_data)  # type: ignore


class TestArtworkDesignPathsValidation:
    """Tests for design_paths field validation."""

    @pytest.fixture
    def valid_placement_path(self):
        """Provide valid placement path with mocked file checks."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        return mock_path

    @pytest.fixture
    def minimal_artwork_data(self, valid_placement_path):
        """Provide minimal valid Artwork data."""
        return {
            "artwork_id": "ART-001",
            "line_item_id": "LI-001",
            "design_url": "https://example.com/design.pdf",
            "placement_url": "https://example.com/placement.pdf",
            "placement_path": valid_placement_path,
        }

    def test_design_paths_required(self, minimal_artwork_data):
        """Test that design_paths is required."""
        with pytest.raises(TypeError):
            Artwork(**minimal_artwork_data)

    def test_design_paths_empty_list_is_accepted(self, minimal_artwork_data):
        """Test that empty design_paths list is accepted (all() returns True for empty list)."""
        artwork = Artwork(design_paths=[], **minimal_artwork_data)
        assert artwork.design_paths == []

    def test_design_paths_not_list_raises_error(self, minimal_artwork_data):
        """Test that non-list design_paths raises ValueError."""
        with pytest.raises(ValueError, match="Design paths must be a list of Path objects"):
            Artwork(design_paths="not a list", **minimal_artwork_data)  # type: ignore

    def test_design_paths_none_raises_error(self, minimal_artwork_data):
        """Test that None design_paths raises ValueError."""
        with pytest.raises(ValueError, match="Design paths must be a list of Path objects"):
            Artwork(design_paths=None, **minimal_artwork_data)  # type: ignore

    def test_design_paths_contains_non_path_raises_error(self, minimal_artwork_data):
        """Test that design_paths containing non-Path objects raises ValueError."""
        with pytest.raises(ValueError, match="Design paths must be a list of Path objects"):
            Artwork(design_paths=["not a Path"], **minimal_artwork_data)  # type: ignore

    def test_design_paths_contains_string_path_raises_error(self, minimal_artwork_data):
        """Test that design_paths containing string paths raises ValueError."""
        with pytest.raises(ValueError, match="Design paths must be a list of Path objects"):
            Artwork(design_paths=["/tmp/design.pdf"], **minimal_artwork_data)  # type: ignore

    def test_design_paths_with_nonexistent_file_raises_error(self, minimal_artwork_data):
        """Test that design_paths with nonexistent files raises ValueError."""
        # Create a Path object that doesn't exist
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = False
        with pytest.raises(ValueError, match="Design paths must be a list of Path objects"):
            Artwork(design_paths=[mock_path], **minimal_artwork_data)

    def test_design_paths_single_valid_path(self, minimal_artwork_data):
        """Test that single valid design path is accepted."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        artwork = Artwork(design_paths=[mock_path], **minimal_artwork_data)
        assert artwork.design_paths == [mock_path]

    def test_design_paths_multiple_valid_paths(self, minimal_artwork_data):
        """Test that multiple valid design paths are accepted."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        artwork = Artwork(design_paths=paths, **minimal_artwork_data)
        assert artwork.design_paths == paths

    def test_design_paths_mixed_valid_and_invalid_raises_error(self, minimal_artwork_data):
        """Test that mix of valid and invalid paths raises ValueError."""
        valid_path = MagicMock(spec=Path)
        valid_path.is_file.return_value = True
        invalid_path = MagicMock(spec=Path)
        invalid_path.is_file.return_value = False
        with pytest.raises(ValueError, match="Design paths must be a list of Path objects"):
            Artwork(design_paths=[valid_path, invalid_path], **minimal_artwork_data)


class TestArtworkPlacementURLValidation:
    """Tests for placement_url field validation."""

    @pytest.fixture
    def valid_design_paths(self):
        """Provide valid design paths with mocked file checks."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        return paths

    @pytest.fixture
    def valid_placement_path(self):
        """Provide valid placement path with mocked file checks."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        return mock_path

    @pytest.fixture
    def minimal_artwork_data(self, valid_design_paths, valid_placement_path):
        """Provide minimal valid Artwork data."""
        return {
            "artwork_id": "ART-001",
            "line_item_id": "LI-001",
            "design_url": "https://example.com/design.pdf",
            "design_paths": valid_design_paths,
            "placement_path": valid_placement_path,
        }

    def test_placement_url_required(self, minimal_artwork_data):
        """Test that placement_url is required."""
        with pytest.raises(TypeError):
            Artwork(**minimal_artwork_data)

    def test_placement_url_empty_raises_error(self, minimal_artwork_data):
        """Test that empty placement_url raises ValueError."""
        with pytest.raises(ValueError, match="Placement URL must be a non-empty string"):
            Artwork(placement_url="", **minimal_artwork_data)

    def test_placement_url_whitespace_only_raises_error(self, minimal_artwork_data):
        """Test that whitespace-only placement_url raises ValueError."""
        with pytest.raises(ValueError, match="Placement URL must be a non-empty string"):
            Artwork(placement_url="   ", **minimal_artwork_data)

    def test_placement_url_not_string_raises_error(self, minimal_artwork_data):
        """Test that non-string placement_url raises ValueError."""
        with pytest.raises(ValueError, match="Placement URL must be a non-empty string"):
            Artwork(placement_url=321, **minimal_artwork_data)  # type: ignore

    def test_placement_url_none_raises_error(self, minimal_artwork_data):
        """Test that None placement_url raises ValueError."""
        with pytest.raises(ValueError, match="Placement URL must be a non-empty string"):
            Artwork(placement_url=None, **minimal_artwork_data)  # type: ignore


class TestArtworkPlacementPathValidation:
    """Tests for placement_path field validation."""

    @pytest.fixture
    def valid_design_paths(self):
        """Provide valid design paths with mocked file checks."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        return paths

    @pytest.fixture
    def minimal_artwork_data(self, valid_design_paths):
        """Provide minimal valid Artwork data."""
        return {
            "artwork_id": "ART-001",
            "line_item_id": "LI-001",
            "design_url": "https://example.com/design.pdf",
            "design_paths": valid_design_paths,
            "placement_url": "https://example.com/placement.pdf",
        }

    def test_placement_path_required(self, minimal_artwork_data):
        """Test that placement_path is required."""
        with pytest.raises(TypeError):
            Artwork(**minimal_artwork_data)

    def test_placement_path_not_path_raises_error(self, minimal_artwork_data):
        """Test that non-Path placement_path raises ValueError."""
        with pytest.raises(ValueError, match="Placement path must be a Path object"):
            Artwork(placement_path="not a Path", **minimal_artwork_data)  # type: ignore

    def test_placement_path_none_raises_error(self, minimal_artwork_data):
        """Test that None placement_path raises ValueError."""
        with pytest.raises(ValueError, match="Placement path must be a Path object"):
            Artwork(placement_path=None, **minimal_artwork_data)  # type: ignore

    def test_placement_path_with_nonexistent_file_raises_error(self, minimal_artwork_data):
        """Test that placement_path with nonexistent file raises ValueError."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = False
        with pytest.raises(ValueError, match="Placement path must be a Path object"):
            Artwork(placement_path=mock_path, **minimal_artwork_data)

    def test_placement_path_valid(self, minimal_artwork_data):
        """Test that valid placement_path is accepted."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        artwork = Artwork(placement_path=mock_path, **minimal_artwork_data)
        assert artwork.placement_path is mock_path


class TestArtworkImmutability:
    """Tests for Artwork immutability (frozen dataclass)."""

    @pytest.fixture
    def artwork(self):
        """Provide an Artwork instance."""
        design_paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            design_paths.append(mock_path)

        placement_path = MagicMock(spec=Path)
        placement_path.is_file.return_value = True

        return Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )

    def test_cannot_modify_artwork_id(self, artwork):
        """Test that artwork_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            artwork.artwork_id = "ART-002"  # type: ignore

    def test_cannot_modify_line_item_id(self, artwork):
        """Test that line_item_id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            artwork.line_item_id = "LI-002"  # type: ignore

    def test_cannot_modify_design_url(self, artwork):
        """Test that design_url cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            artwork.design_url = "https://example.com/newdesign.pdf"  # type: ignore

    def test_cannot_modify_design_paths(self, artwork):
        """Test that design_paths cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            artwork.design_paths = []  # type: ignore

    def test_cannot_modify_placement_url(self, artwork):
        """Test that placement_url cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            artwork.placement_url = "https://example.com/newplacement.pdf"  # type: ignore

    def test_cannot_modify_placement_path(self, artwork):
        """Test that placement_path cannot be modified."""
        path = Path("/tmp/newplacement.pdf")
        with pytest.raises((AttributeError, TypeError)):
            artwork.placement_path = path  # type: ignore


class TestArtworkRepresentation:
    """Tests for Artwork string representation."""

    @pytest.fixture
    def artwork(self):
        """Provide an Artwork instance."""
        design_paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            design_paths.append(mock_path)

        placement_path = MagicMock(spec=Path)
        placement_path.is_file.return_value = True

        return Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )

    def test_repr_contains_class_name(self, artwork):
        """Test that repr contains Artwork class name."""
        repr_str = repr(artwork)
        assert "Artwork" in repr_str

    def test_repr_contains_artwork_id(self, artwork):
        """Test that repr contains artwork_id value."""
        repr_str = repr(artwork)
        assert "ART-001" in repr_str

    def test_repr_contains_id(self, artwork):
        """Test that repr contains the auto-generated id."""
        repr_str = repr(artwork)
        assert str(artwork.id) in repr_str


class TestArtworkEquality:
    """Tests for Artwork equality comparison."""

    @pytest.fixture
    def design_paths(self):
        """Provide mocked design paths."""
        paths = []
        for _i in range(2):
            mock_path = MagicMock(spec=Path)
            mock_path.is_file.return_value = True
            paths.append(mock_path)
        return paths

    @pytest.fixture
    def placement_path(self):
        """Provide mocked placement path."""
        mock_path = MagicMock(spec=Path)
        mock_path.is_file.return_value = True
        return mock_path

    def test_same_instance_equals_itself(self, design_paths, placement_path):
        """Test that an artwork equals itself."""
        artwork = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        assert artwork == artwork

    def test_different_instances_same_data_are_not_equal(self, design_paths, placement_path):
        """Test that two instances with same data are equal (dataclass default behavior)."""
        artwork1 = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        artwork2 = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        # Dataclasses with the same field values are equal
        assert artwork1 != artwork2

    def test_different_artwork_id_not_equal(self, design_paths, placement_path):
        """Test that artworks with different artwork_ids are not equal."""
        artwork1 = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        artwork2 = Artwork(
            artwork_id="ART-002",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        assert artwork1 != artwork2

    def test_different_line_item_id_not_equal(self, design_paths, placement_path):
        """Test that artworks with different line_item_ids are not equal."""
        artwork1 = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        artwork2 = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-002",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        assert artwork1 != artwork2

    def test_auto_generated_ids_make_instances_not_equal(self, design_paths, placement_path):
        """Test that auto-generated IDs ensure different instances are not equal."""
        # Even with identical data, different instances have different IDs
        artwork1 = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        artwork2 = Artwork(
            artwork_id="ART-001",
            line_item_id="LI-001",
            design_url="https://example.com/design.pdf",
            design_paths=design_paths,
            placement_url="https://example.com/placement.pdf",
            placement_path=placement_path,
        )
        # Different instances should not be equal due to different auto-generated IDs
        assert artwork1 != artwork2
        assert artwork1.id != artwork2.id
