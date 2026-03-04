"""Harman stock transfer service implementation.

This module provides the HarmanStockService, which reads inbound stock transfer
notifications (delivery advice) from Harman via XML files and sends confirmations
back. It implements the IStockService protocol.

Key responsibilities:
- Reading XML stock transfer notification files from input directory
- Parsing EDIFACT DELVRY03 data structure into transfer information
- Extracting delivery numbers, item details, quantities, and locations
- Generating XML acknowledgment replies in IN05 format
- Sending email notifications with reply attachments to configured recipient
- Renaming processed files to prevent re-processing

The service is configured from application settings and integrates with email
notification system for supplier communication.
"""

import datetime as dt
from collections.abc import Generator
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any, Self

import xmltodict  # type: ignore
from redmail.email.sender import EmailSender

from src.app.errors import ErrorStore
from src.config import Config, get_config

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class HarmanStockService:
    """Harman stock transfer service for reading and confirming deliveries.

    This service reads inbound stock transfer (delivery advice) notifications
    from Harman in XML format and manages their lifecycle: reading, parsing,
    generating acknowledgment replies, and notifying via email.

    All fields are configuration values that define where to read and write
    stock transfer communications.

    This class enforces:
    - Frozen: All attributes are read-only after creation (configured via from_config)
    - Harman-specific formatting: XML parsing and EDIFACT structure generation
    - Proper error handling with ErrorStore singleton
    - Email integration for supplier notifications

    Attributes:
        input_dir: Path to directory containing inbound stock transfer XML files
        output_dir: Path to directory for output acknowledgment reply files

    Example:
        >>> service = HarmanStockService.from_config(config)
        >>> for transfer in service.read_stock_transfers():
        ...     print(f"Processing delivery {transfer['delivery_number']}")
        ...     service.reply_stock_transfer(transfer)
    """

    input_dir: Path
    output_dir: Path

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create a HarmanStockService instance from application configuration.

        Factory method that builds a HarmanStockService with all settings from
        the application configuration object. This is the standard way to
        instantiate the service.

        Args:
            config: Application Config instance with Harman stock service settings

        Returns:
            Fully initialized HarmanStockService ready to process stock transfers
        """
        return cls(
            input_dir=config.harman_input_dir,
            output_dir=config.harman_output_dir,
        )

    def read_stock_transfers(self) -> Generator[dict[str, Any], None, None]:
        """Generate stock transfer notifications from input XML files.

        Scans the input directory for *.xml files, parses each as EDIFACT
        delivery advice data, and yields transfer information dictionaries.
        Errors during parsing are caught and stored without stopping iteration
        of remaining files.

        Yields:
            Dictionary with keys:
            - 'file_path': Path to the input XML file
            - 'idoc_number': EDIFACT control document number
            - 'idoc_datetime': Timestamp from the delivery advice
            - 'delivery_number': Harman delivery reference number
            - 'items': List of transfer items with quantity, location, etc.

        Note:
            Files are processed in sorted order for consistency. Files with parse
            errors are logged but don't prevent processing of other files.
        """
        for file_path in self.input_dir.glob("*.xml", case_sensitive=False):
            try:
                logger.info("Reading stock transfer file: %s", file_path.name)
                transfer_data = xmltodict.parse(file_path.read_text(encoding="utf-8"))
                yield self._get_transfer_info(transfer_data, file_path)
            except Exception as exc:
                ErrorStore().add(exc)

    def _get_transfer_info(self, transfer_data: dict[str, Any], file_path: Path) -> dict[str, Any]:
        """Extract transfer information from parsed XML delivery advice data.

        Parses the EDIFACT DELVRY03/IDOC structure containing delivery advice
        and extracts relevant information about the delivery, items, quantities,
        and locations into a structured dictionary for processing.

        Handles xmltodict quirk where single items return as dict instead of list.

        Args:
            transfer_data: EDIFACT data parsed by xmltodict from XML file
            file_path: Path to the source XML file

        Returns:
            Dictionary with transfer information:
            - 'file_path': String path to input file
            - 'idoc_number': EDIFACT document number (DOCNUM)
            - 'idoc_datetime': Parsed timestamp from CREDAT and CRETIM
            - 'delivery_number': Delivery reference (VBELN)
            - 'items': List of items with item_number, product_code, quantity, storage_location

        Raises:
            Exception: If required EDIFACT structure elements are missing or unparseable
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

    def reply_stock_transfer(self, transfer_data: dict[str, Any]) -> None:
        """Generate and send acknowledgment reply for a stock transfer.

        Creates an XML acknowledgment (IN05 format) confirming receipt of the
        stock transfer, writes it to a file in the output directory, emails it
        to the configured recipient, and renames the input file to mark it as
        processed.

        The reply includes:
        - Matching document number from the original delivery advice
        - Message direction and code indicating successful processing
        - Echoed delivery details and item information
        - Storage location status for inventory tracking

        Args:
            transfer_data: Dictionary with transfer information from read_stock_transfers()
                          Must contain delivery_number, items, idoc_number, idoc_datetime,
                          and file_path keys.

        Raises:
            May raise exceptions if file writing or email sending fails

        Side effects:
            - Creates IN05 reply XML file in output directory
            - Sends email with attachments to configured recipient
            - Renames input file with .replied extension to prevent re-processing
        """
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

        logger.info("Generated reply data for delivery: %s", transfer_data.get("delivery_number"))
        reply = xmltodict.unparse(reply_data, pretty=True)
        reply_path = (
            self.output_dir / f"harman_in05_{transfer_data.get('delivery_number')}.xml".upper()
        )
        reply_path.write_text(reply, encoding="utf-8")
        logger.info("Written reply file for delivery: %s", transfer_data.get("delivery_number"))

        # email the reply file to the configured recipient
        config = get_config()
        emailer = EmailSender(host=config.smtp_host, port=config.smtp_port, use_starttls=True)
        emailer.send(
            subject=f"Harman Stock Transfer Reply for Delivery {transfer_data.get('delivery_number')}",
            sender=config.email_sender,
            receivers=config.email_stock_to,
            html_template="stock_email.html",
            body_params={
                "stock_transfer": transfer_data,
                "supplier_name": config.harman_stock_supplier_name,
                "upload_link": config.harman_stock_upload_link,
                "support_email": config.email_alert_to,
                "company_name": config.sale_company_name,
            },
            attachments={reply_path.name: reply_path.read_bytes()},
        )

        # Rename the processed input file, to prevent reprocessing.
        input_file_path = Path(transfer_data.get("file_path", ""))
        if input_file_path.exists():
            replied_path = input_file_path.parent / f"{input_file_path.stem}.replied"
            input_file_path.rename(replied_path)
