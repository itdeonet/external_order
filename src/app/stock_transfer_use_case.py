"""Stock transfer request processing use case.

Process inbound stock transfer delivery notifications from multiple providers.
"""

from dataclasses import dataclass, field
from logging import getLogger

from src.app.errors import get_error_store
from src.app.registry import get_stock_services, get_use_cases
from src.domain import IRegistry, IStockService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class StockTransferUseCase:
    """Use case for processing and replying to stock transfer requests.

    Reads transfer requests, processes them, and sends confirmations.
    Handles errors per-transfer without stopping processing.
    """

    stock_services: IRegistry[IStockService] = field(default_factory=get_stock_services)

    @classmethod
    def register(cls, name: str) -> None:
        """Factory method to create and register a StockTransferUseCase instance."""
        logger.info("Register StockTransferUseCase with name '%s'", name)
        use_case = cls()
        get_use_cases().register(name, use_case)

    def execute(self) -> None:
        """Process stock transfer requests across all registered stock service providers.

        Multi-provider orchestration workflow:
        1. For each stock service provider (e.g., Harman, Camelbak):
           a. Read all pending stock transfer requests from that provider
           b. For each transfer request:
              i. Create a stock transfer reply (DESADV EDI or equivalent format)
              ii. Send confirmation email with the reply
              iii. Mark transfer as processed

        Errors at provider or individual transfer levels are caught and stored without
        stopping processing of remaining transfers, enabling graceful degradation.
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
                    reply_path = stock_service.create_stock_transfer_reply(transfer_data)
                    stock_service.email_stock_transfer_reply(reply_path, transfer_data)
                    stock_service.mark_transfer_as_processed(transfer_data)
                except Exception as exc:
                    logger.exception(
                        "Error processing stock transfer request %s from %s service.",
                        transfer_data.get("id"),
                        stock_service_name,
                    )
                    get_error_store().add(exc)
