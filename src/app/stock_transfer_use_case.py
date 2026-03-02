"""Stock Transfer Use Case"""

from dataclasses import dataclass
from logging import getLogger

from src.app.errors import ErrorStore
from src.interfaces import IRegistry, IStockService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class StockTransferUseCase:
    """Use case for transferring stock between locations."""

    stock_services: IRegistry[IStockService]

    def execute(self) -> None:
        """Execute the stock transfer."""
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
