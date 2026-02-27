"""Harman order service implementation."""

import datetime as dt
from collections.abc import Generator
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any, Self

import xmltodict  # type: ignore

from src.config import Config
from src.interfaces import IErrorQueue

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class HarmanStockService:
    """Harman stock service implementation."""

    input_dir: Path
    output_dir: Path

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create a HarmanStockService instance from settings."""
        return cls(
            input_dir=config.harman_input_dir,
            output_dir=config.harman_output_dir,
        )

    def read_stock_transfers(
        self, error_queue: IErrorQueue
    ) -> Generator[dict[str, Any], None, None]:
        """Read stock transfer requests."""
        for file_path in self.input_dir.glob("*.xml", case_sensitive=False):
            try:
                logger.info("Reading stock transfer file: %s", file_path.name)
                transfer_data = xmltodict.parse(file_path.read_text(encoding="utf-8"))
                yield self._get_transfer_info(transfer_data, file_path)
            except Exception as exc:
                error_queue.put(exc)

    def _get_transfer_info(self, transfer_data: dict[str, Any], file_path: Path) -> dict[str, Any]:
        """Extract relevant information from the stock transfer data."""
        idoc: dict = transfer_data.get("DELVRY03", {}).get("IDOC", {})
        control: dict = idoc.get("EDI_DC40", {})
        header: dict = idoc.get("E1EDL20", {})
        items_raw: dict = header.get("E1EDL24", [])
        # xmldict returns a dict for single items, list for multiple
        items = items_raw if isinstance(items_raw, list) else ([items_raw] if items_raw else [])

        transfer_info = {
            "file_path": str(file_path),
            "idoc_number": control.get("DOCNUM"),
            "idoc_datetime": dt.datetime.strptime(
                f"{control.get('CREDAT')}{control.get('CRETIM')}+0000",
                "%Y%m%d%H%M%S%z",
            ),
            "delivery_number": header.get("VBELN"),
            "items": [
                {
                    "item_number": item.get("POSNR"),
                    "product_sku": item.get("MATNR"),
                    "quantity": int(float(item.get("LFIMG", 0))),
                    "storage_location": item.get("LGORT"),
                }
                for item in items
            ],
        }

        logger.debug(
            "Parsed stock transfer data for delivery: %s", transfer_info.get("delivery_number")
        )
        return transfer_info

    def reply_stock_transfer(self, transfer_data: dict[str, Any]) -> None:
        """Reply to stock transfer requests."""
        # create reply file with same name as input but with .reply extension
        logger.info(
            "Processing stock transfer data for delivery: %s",
            transfer_data.get("delivery_number"),
        )
        create_time: dt.datetime = transfer_data.get("idoc_datetime", dt.datetime.now())
        reply_data = {
            "HARMAN": {
                "IDOC": {
                    "EDI_DC40": {
                        "DOCNUM": transfer_data.get("idoc_number"),
                        "DIRECT": "2",
                        "INTCODE": "IN05",
                        "CREDAT": create_time.strftime("%Y-%m-%d"),
                        "CRETIM": create_time.strftime("%H:%M:%S"),
                    },
                    "E1EDL20": {
                        "VBELN": transfer_data.get("delivery_number"),
                        "E1EDL24": [
                            {
                                "POSNR": item["item_number"],
                                "MATNR": item["product_sku"],
                                "BATCH": "CLEAR",
                                "STKSTA": f"{item['storage_location']}UN",
                                "DELQTY": str(item["quantity"]),
                            }
                            for item in transfer_data.get("items", [])
                        ],
                    },
                },
            },
        }

        logger.info("Generated reply data for delivery: %s", transfer_data.get("delivery_number"))
        reply = xmltodict.unparse(reply_data, pretty=True)
        reply_path = (
            self.output_dir / f"harman_in05_{transfer_data.get('delivery_number')}.xml".upper()
        )
        reply_path.write_text(reply, encoding="utf-8")
        logger.info("Written reply file for delivery: %s", transfer_data.get("delivery_number"))

        # Rename the processed input file, to prevent reprocessing.
        input_file_path = Path(transfer_data.get("file_path", ""))
        if input_file_path.exists():
            replied_path = input_file_path.parent / f"{input_file_path.stem}.replied"
            input_file_path.rename(replied_path)
