"""Unit tests for HarmanStockService."""

import datetime as dt
from pathlib import Path

import pytest

from src.app.errors import ErrorStore
from src.services.harman_stock_service import HarmanStockService


@pytest.fixture
def mock_config(mocker):
    """Create a mock config object."""
    mock = mocker.Mock()
    mock.harman_input_dir = Path("/input")
    mock.harman_output_dir = Path("/output")
    return mock


class TestHarmanStockServiceInstantiation:
    """Tests for HarmanStockService instantiation."""

    def test_instantiation_with_all_fields(self, tmp_path):
        """Test creating HarmanStockService with all fields."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(
            input_dir=input_dir,
            output_dir=output_dir,
        )

        assert service.input_dir == input_dir
        assert service.output_dir == output_dir

    def test_instantiation_creates_frozen_dataclass(self, tmp_path):
        """Test that HarmanStockService is a frozen dataclass."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(
            input_dir=input_dir,
            output_dir=output_dir,
        )

        with pytest.raises(AttributeError):
            service.input_dir = tmp_path  # type: ignore


class TestHarmanStockServiceReadStockTransfers:
    """Tests for read_stock_transfers method."""

    @pytest.fixture
    def sample_xml_data(self):
        """Provide sample XML data for testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<DELVRY03>
    <IDOC>
        <EDI_DC40>
            <DOCNUM>123456</DOCNUM>
            <CREDAT>20240101</CREDAT>
            <CRETIM>143000</CRETIM>
        </EDI_DC40>
        <E1EDL20>
            <VBELN>DEL-001</VBELN>
            <E1EDL24>
                <POSNR>001</POSNR>
                <MATNR>PROD-001</MATNR>
                <LFIMG>50.00</LFIMG>
                <LGORT>WAREHOUSE</LGORT>
            </E1EDL24>
        </E1EDL20>
    </IDOC>
</DELVRY03>
"""

    def test_read_stock_transfers_with_no_files(self, tmp_path):
        """Test read_stock_transfers when input directory is empty."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfers = list(service.read_stock_transfers())

        assert transfers == []

    def test_read_stock_transfers_with_single_xml_file(self, tmp_path, sample_xml_data, mocker):
        """Test read_stock_transfers with a single XML file."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        xml_file = input_dir / "transfer.xml"
        xml_file.write_text(sample_xml_data)

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        with mocker.patch(
            "src.services.harman_stock_service.HarmanStockService._get_transfer_info",
            return_value={"id": "transfer_1"},
        ):
            transfers = list(service.read_stock_transfers())

        assert len(transfers) == 1
        assert transfers[0] == {"id": "transfer_1"}

    def test_read_stock_transfers_with_multiple_xml_files(self, tmp_path, sample_xml_data, mocker):
        """Test read_stock_transfers with multiple XML files."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create multiple XML files
        for i in range(3):
            xml_file = input_dir / f"transfer_{i}.xml"
            xml_file.write_text(sample_xml_data)

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        with mocker.patch(
            "src.services.harman_stock_service.HarmanStockService._get_transfer_info",
            side_effect=[{"id": f"t{i}"} for i in range(3)],
        ):
            transfers = list(service.read_stock_transfers())

        assert len(transfers) == 3

    def test_read_stock_transfers_ignores_non_xml_files(self, tmp_path, sample_xml_data, mocker):
        """Test that read_stock_transfers only processes XML files."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        xml_file = input_dir / "transfer.xml"
        xml_file.write_text(sample_xml_data)

        # Create non-XML files
        (input_dir / "readme.txt").write_text("Not XML")
        (input_dir / "data.json").write_text("{}")

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        with mocker.patch(
            "src.services.harman_stock_service.HarmanStockService._get_transfer_info",
            return_value={"id": "t1"},
        ):
            transfers = list(service.read_stock_transfers())

        assert len(transfers) == 1

    def test_read_stock_transfers_handles_xml_parse_error(self, tmp_path, mocker):
        """Test that read_stock_transfers handles XML parsing errors."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create invalid XML file
        xml_file = input_dir / "invalid.xml"
        xml_file.write_text("Not valid XML <unclosed>")

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        # Mock ErrorStore singleton so we can verify add() was called
        mock_error_store = mocker.Mock(spec=ErrorStore)
        mocker.patch("src.services.harman_stock_service.ErrorStore", return_value=mock_error_store)

        transfers = list(service.read_stock_transfers())

        # Should catch the error and store it
        assert len(transfers) == 0
        assert mock_error_store.add.called

    def test_read_stock_transfers_calls_get_transfer_info(self, tmp_path, sample_xml_data, mocker):
        """Test that read_stock_transfers calls _get_transfer_info."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        xml_file = input_dir / "transfer.xml"
        xml_file.write_text(sample_xml_data)

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        mock_get_info = mocker.patch(
            "src.services.harman_stock_service.HarmanStockService._get_transfer_info",
            return_value={"id": "t1"},
        )
        list(service.read_stock_transfers())

        assert mock_get_info.called

    def test_read_stock_transfers_case_insensitive_extension(
        self, tmp_path, sample_xml_data, mocker
    ):
        """Test that XML file matching is case-insensitive."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create file with uppercase extension
        xml_file = input_dir / "transfer.XML"
        xml_file.write_text(sample_xml_data)

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        with mocker.patch(
            "src.services.harman_stock_service.HarmanStockService._get_transfer_info",
            return_value={"id": "t1"},
        ):
            transfers = list(service.read_stock_transfers())

        assert len(transfers) == 1


class TestHarmanStockServiceGetTransferInfo:
    """Tests for _get_transfer_info method."""

    def test_get_transfer_info_with_complete_data(self, tmp_path):
        """Test parsing complete transfer data."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfer_data = {
            "DELVRY03": {
                "IDOC": {
                    "EDI_DC40": {
                        "DOCNUM": "123456",
                        "CREDAT": "20240315",
                        "CRETIM": "143000",
                    },
                    "E1EDL20": {
                        "VBELN": "DEL-001",
                        "E1EDL24": [
                            {
                                "POSNR": "001",
                                "MATNR": "PROD-001",
                                "LFIMG": "50.00",
                                "LGORT": "WAREHOUSE",
                            }
                        ],
                    },
                }
            }
        }
        file_path = tmp_path / "test.xml"

        result = service._get_transfer_info(transfer_data, file_path)

        assert result["file_path"] == str(file_path)
        assert result["idoc_number"] == "123456"
        assert result["delivery_number"] == "DEL-001"
        assert len(result["items"]) == 1
        assert result["items"][0]["product_code"] == "PROD-001"
        assert result["items"][0]["quantity"] == 50
        assert result["items"][0]["storage_location"] == "WAREHOUSE"

    def test_get_transfer_info_with_multiple_items(self, tmp_path):
        """Test parsing transfer data with multiple items."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfer_data = {
            "DELVRY03": {
                "IDOC": {
                    "EDI_DC40": {
                        "DOCNUM": "123456",
                        "CREDAT": "20240315",
                        "CRETIM": "143000",
                    },
                    "E1EDL20": {
                        "VBELN": "DEL-001",
                        "E1EDL24": [
                            {
                                "POSNR": "001",
                                "MATNR": "PROD-001",
                                "LFIMG": "50.00",
                                "LGORT": "WAREHOUSE",
                            },
                            {
                                "POSNR": "002",
                                "MATNR": "PROD-002",
                                "LFIMG": "30.50",
                                "LGORT": "STOCKROOM",
                            },
                        ],
                    },
                }
            }
        }
        file_path = tmp_path / "test.xml"

        result = service._get_transfer_info(transfer_data, file_path)

        assert len(result["items"]) == 2
        assert result["items"][0]["product_code"] == "PROD-001"
        assert result["items"][1]["product_code"] == "PROD-002"
        assert result["items"][1]["quantity"] == 30

    def test_get_transfer_info_with_single_item_dict(self, tmp_path):
        """Test parsing when single item returns dict instead of list."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfer_data = {
            "DELVRY03": {
                "IDOC": {
                    "EDI_DC40": {
                        "DOCNUM": "123456",
                        "CREDAT": "20240315",
                        "CRETIM": "143000",
                    },
                    "E1EDL20": {
                        "VBELN": "DEL-001",
                        "E1EDL24": {  # Single item is a dict
                            "POSNR": "001",
                            "MATNR": "PROD-001",
                            "LFIMG": "50.00",
                            "LGORT": "WAREHOUSE",
                        },
                    },
                }
            }
        }
        file_path = tmp_path / "test.xml"

        result = service._get_transfer_info(transfer_data, file_path)

        assert len(result["items"]) == 1
        assert result["items"][0]["product_code"] == "PROD-001"

    def test_get_transfer_info_with_no_items(self, tmp_path):
        """Test parsing when no items are present."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfer_data = {
            "DELVRY03": {
                "IDOC": {
                    "EDI_DC40": {
                        "DOCNUM": "123456",
                        "CREDAT": "20240315",
                        "CRETIM": "143000",
                    },
                    "E1EDL20": {
                        "VBELN": "DEL-001",
                    },
                }
            }
        }
        file_path = tmp_path / "test.xml"

        result = service._get_transfer_info(transfer_data, file_path)

        assert len(result["items"]) == 0

    def test_get_transfer_info_parses_datetime_correctly(self, tmp_path):
        """Test that datetime is parsed correctly."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfer_data = {
            "DELVRY03": {
                "IDOC": {
                    "EDI_DC40": {
                        "DOCNUM": "123456",
                        "CREDAT": "20240315",
                        "CRETIM": "143000",
                    },
                    "E1EDL20": {
                        "VBELN": "DEL-001",
                        "E1EDL24": [],
                    },
                }
            }
        }
        file_path = tmp_path / "test.xml"

        result = service._get_transfer_info(transfer_data, file_path)

        assert isinstance(result["idoc_datetime"], dt.datetime)
        assert result["idoc_datetime"].year == 2024
        assert result["idoc_datetime"].month == 3
        assert result["idoc_datetime"].day == 15
        assert result["idoc_datetime"].hour == 14
        assert result["idoc_datetime"].minute == 30
        assert result["idoc_datetime"].second == 0


class TestHarmanStockServiceReplyStockTransfer:
    """Tests for reply_stock_transfer method."""

    def test_reply_stock_transfer_creates_output_file(self, tmp_path):
        """Test that reply_stock_transfer creates an output file."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfer_data = {
            "file_path": str(input_dir / "transfer.xml"),
            "idoc_number": "123456",
            "idoc_datetime": dt.datetime(2024, 3, 15, 14, 30, 0),
            "delivery_number": "DEL-001",
            "items": [
                {
                    "item_number": "001",
                    "product_code": "PROD-001",
                    "quantity": 50,
                    "storage_location": "WAREHOUSE",
                }
            ],
        }

        # Create the input file first
        file_path = Path(transfer_data["file_path"])
        file_path.write_text("<xml></xml>")

        service.reply_stock_transfer(transfer_data)

        # Check that output file was created with uppercase filename
        output_files = list(output_dir.glob("*.XML"))
        assert len(output_files) == 1
        assert "HARMAN_IN05_DEL-001" in output_files[0].name

    def test_reply_stock_transfer_creates_valid_xml(self, tmp_path):
        """Test that reply_stock_transfer creates valid XML output."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        file_path = tmp_path / "transfer.xml"
        file_path.write_text("<xml></xml>")

        transfer_data = {
            "file_path": str(file_path),
            "idoc_number": "123456",
            "idoc_datetime": dt.datetime(2024, 3, 15, 14, 30, 0),
            "delivery_number": "DEL-001",
            "items": [
                {
                    "item_number": "001",
                    "product_code": "PROD-001",
                    "quantity": 50,
                    "storage_location": "WAREHOUSE",
                }
            ],
        }

        service.reply_stock_transfer(transfer_data)

        output_files = list(output_dir.glob("*.XML"))
        assert len(output_files) == 1
        output_content = output_files[0].read_text()

        assert "<?xml" in output_content
        assert "HARMAN" in output_content
        assert "123456" in output_content
        assert "DEL-001" in output_content

    def test_reply_stock_transfer_renames_input_file(self, tmp_path):
        """Test that reply_stock_transfer renames the input file."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        input_file = input_dir / "transfer.xml"
        input_file.write_text("<xml></xml>")

        transfer_data = {
            "file_path": str(input_file),
            "idoc_number": "123456",
            "idoc_datetime": dt.datetime(2024, 3, 15, 14, 30, 0),
            "delivery_number": "DEL-001",
            "items": [],
        }

        service.reply_stock_transfer(transfer_data)

        # Original file should be renamed
        assert not input_file.exists()
        replied_file = input_dir / "transfer.replied"
        assert replied_file.exists()

    def test_reply_stock_transfer_with_multiple_items(self, tmp_path):
        """Test reply_stock_transfer with multiple items."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        input_file = input_dir / "transfer.xml"
        input_file.write_text("<xml></xml>")

        transfer_data = {
            "file_path": str(input_file),
            "idoc_number": "123456",
            "idoc_datetime": dt.datetime(2024, 3, 15, 14, 30, 0),
            "delivery_number": "DEL-001",
            "items": [
                {
                    "item_number": "001",
                    "product_code": "PROD-001",
                    "quantity": 50,
                    "storage_location": "WAREHOUSE",
                },
                {
                    "item_number": "002",
                    "product_code": "PROD-002",
                    "quantity": 30,
                    "storage_location": "STOCKROOM",
                },
            ],
        }

        service.reply_stock_transfer(transfer_data)

        output_files = list(output_dir.glob("*.XML"))
        assert len(output_files) == 1

    def test_reply_stock_transfer_handles_missing_input_file(self, tmp_path):
        """Test that reply_stock_transfer handles missing input file gracefully."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        service = HarmanStockService(input_dir=input_dir, output_dir=output_dir)

        transfer_data = {
            "file_path": str(input_dir / "nonexistent.xml"),
            "idoc_number": "123456",
            "idoc_datetime": dt.datetime(2024, 3, 15, 14, 30, 0),
            "delivery_number": "DEL-001",
            "items": [],
        }

        # Should not raise an error
        service.reply_stock_transfer(transfer_data)

        output_files = list(output_dir.glob("*.XML"))
        assert len(output_files) == 1
