"""Stock transfer request processing use case.

This module handles the processing of inbound stock transfer delivery notifications
from multiple stock service providers. It reads transfer requests, processes them,
and sends confirmations back to the providers. Errors at the individual transfer
level are caught and stored without interrupting processing of other transfers.
"""

from dataclasses import dataclass
from logging import getLogger

from src.app.errors import ErrorStore
from src.interfaces import IRegistry, IStockService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class StockTransferUseCase:
    """Use case for processing and replying to stock transfer requests.

    This use case orchestrates the processing of inbound stock transfer delivery
    notifications from multiple stock service providers (e.g., Harman). For each
    transfer request received:

    1. Reads the transfer data (delivery information, items, quantities)
    2. Processes/replies to the transfer request with confirmation
    3. Catches and stores any errors without stopping other transfers

    Errors are handled at the individual transfer level, allowing processing
    to continue with subsequent transfers even if one fails.

    Attributes:
        stock_services: Registry of stock service providers to monitor for transfers.
    """

    stock_services: IRegistry[IStockService]

    def execute(self) -> None:
        """Process all pending stock transfer requests from registered providers.

        For each registered stock service:
        1. Monitors for inbound stock transfer delivery notifications
        2. For each transfer request received:
           - Parses the transfer data (delivery number, items, quantities, etc.)
           - Processes and replies to the transfer request
           - Records the confirmation
        3. Catches any errors and stores them without stopping other transfers

        Transfer-level errors (parsing, processing, confirmation) are caught,
        logged, and stored in ErrorStore. Processing continues with the next
        transfer request and the next service.

        All caught exceptions are stored in the ErrorStore singleton for later
        review and error reporting.
        """
        logger.info("Process stock transfers for all stock services...")
        for stock_service_name, stock_service in self.stock_services.items():
            logger.info("Process stock transfer from %s service...", stock_service_name)

            # process stock transfer requests
            for transfer_data in stock_service.read_stock_transfers():
                try:
                    logger.info(
                        "Reply to stock transfer request %s from %s service.",
                        transfer_data.get("id"),
                        stock_service_name,
                    )
                    stock_service.reply_stock_transfer(transfer_data)
                except Exception as exc:
                    logger.exception(
                        "Error processing stock transfer request %s from %s service.",
                        transfer_data.get("id"),
                        stock_service_name,
                    )
                    ErrorStore().add(exc)
