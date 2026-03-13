"""Harman stock transfer processing service.

Parses inbound delivery XMLs, extracts transfer info, writes IN05 replies,
and emails confirmations.
"""

import datetime as dt
from collections.abc import Generator
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from typing import Any

import xmltodict  # type: ignore
from redmail.email.sender import EmailSender

from src.app.errors import get_error_store
from src.config import get_config

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class HarmanStockService:
    """Read and acknowledge Harman stock transfer XMLs.

    Config-driven; fields specify `input_dir` and `output_dir` locations.
    """

    input_dir: Path = field(default_factory=lambda: Path(get_config().harman_input_dir))
    output_dir: Path = field(default_factory=lambda: Path(get_config().harman_output_dir))

    def read_stock_transfers(self) -> Generator[dict[str, Any], None, None]:
        """Parse XML files and yield stock transfer info.

        Scans input_dir for *.xml files, parses each, and yields transfer data.

        Yields:
            Dict: Stock transfer data with file_path, idoc_number, items, etc.

        Note:
            Parsing errors are added to ErrorStore and iteration continues.
        """
        for file_path in self.input_dir.glob("*in04*.xml", case_sensitive=False):
            try:
                logger.info("Read stock transfer file: %s", file_path.name)
                transfer_data = xmltodict.parse(file_path.read_text(encoding="utf-8"))
                yield self._get_transfer_info(transfer_data, file_path)
            except Exception as exc:
                get_error_store().add(exc)

    def _get_transfer_info(self, transfer_data: dict[str, Any], file_path: Path) -> dict[str, Any]:
        """Extract and normalize stock transfer info from parsed XML.

        Args:
            transfer_data: Parsed XML dict (DELVRY03 IDOC).
            file_path: Source XML file path.

        Returns:
            Dict with file_path, idoc_number, idoc_datetime, delivery_number, items.
        """
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
                    "product_code": item.get("MATNR"),
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

    def create_stock_transfer_reply(self, transfer_data: dict[str, Any]) -> Path:
        """Create a reply for the stock transfer received.

        Args:
            transfer_data: Stock transfer data with delivery_number, items, etc.

        Returns:
            Path: Path to the created reply file.

        Raises:
            Exception: If file writing fails.
        """
        # create reply file with same name as input but with .reply extension
        logger.info(
            "Processing stock transfer data for delivery: %s",
            transfer_data.get("delivery_number"),
        )
        created_at: dt.datetime = transfer_data.get("idoc_datetime", dt.datetime.now())
        reply_data = {
            "HARMAN": {
                "IDOC": {
                    "EDI_DC40": {
                        "DOCNUM": transfer_data.get("idoc_number"),
                        "DIRECT": "2",
                        "INTCODE": "IN05",
                        "CREDAT": created_at.strftime("%Y-%m-%d"),
                        "CRETIM": created_at.strftime("%H:%M:%S"),
                    },
                    "E1EDL20": {
                        "VBELN": transfer_data.get("delivery_number"),
                        "E1EDL24": [
                            {
                                "POSNR": item["item_number"],
                                "MATNR": item["product_code"],
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

        logger.info("Created reply data for delivery: %s", transfer_data.get("delivery_number"))
        reply = xmltodict.unparse(reply_data, pretty=True)
        reply_path = (
            self.output_dir / f"harman_in05_{transfer_data.get('delivery_number')}.xml".upper()
        )
        reply_path.write_text(reply, encoding="utf-8")
        logger.info("Written reply file for delivery: %s", transfer_data.get("delivery_number"))
        return reply_path

    def email_stock_transfer_reply(self, reply_path: Path, transfer_data: dict[str, Any]) -> None:
        """Email the stock transfer reply.

        Args:
            reply_path: Path to the reply file.
            transfer_data: Stock transfer data with delivery_number, items, etc.

        Raises:
            Exception: If file reading or email sending fails.
        """
        # create reply file with same name as input but with .reply extension
        logger.info("Emailing stock transfer reply for file: %s", reply_path.name)
        # email the reply file to the configured recipient
        config = get_config()
        emailer = EmailSender(host=config.smtp_host, port=config.smtp_port, use_starttls=True)
        emailer.set_template_paths(config.templates_dir)
        emailer.send(
            subject=f"Harman Stock Transfer Reply for Delivery {transfer_data.get('delivery_number')}",
            sender=config.email_sender,
            receivers=config.email_stock_to,
            html_template=config.email_stock_template.name,
            body_params={
                "stock_transfer": transfer_data,
                "supplier_name": config.harman_stock_supplier_name,
                "upload_link": config.harman_stock_upload_link,
                "support_email": config.email_alert_to,
                "company_name": config.sale_company_name,
            },
            attachments={reply_path.name: reply_path.read_bytes()},
        )

    def mark_transfer_as_processed(self, transfer_data: dict[str, Any]) -> None:
        """Mark the stock transfer as processed by renaming the input file."""
        input_file_path = Path(transfer_data.get("file_path", ""))
        if input_file_path.exists():
            processed_path = input_file_path.parent / f"{input_file_path.name}.processed".upper()
            input_file_path.rename(processed_path)
