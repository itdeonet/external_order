"""Main entry point for the application."""

from logging import getLogger
from typing import TYPE_CHECKING

import httpx

from src.app.completed_sale_use_case import CompletedSaleUseCase
from src.app.errors import ErrorQueue
from src.app.new_sale_use_case import NewSaleUseCase
from src.app.odoo_auth import OdooAuth
from src.app.registry import Registry
from src.app.stock_transfer_use_case import StockTransferUseCase
from src.config import Config, get_config
from src.interfaces import (
    IArtworkService,
    IOrderService,
    ISaleService,
    IStockService,
    IUseCase,
)
from src.services.harman_order_service import HarmanOrderService
from src.services.harman_stock_service import HarmanStockService
from src.services.odoo_sale_service import OdooSaleService
from src.services.spectrum_artwork_service import SpectrumArtworkService

if TYPE_CHECKING:
    from src.interfaces import IErrorQueue, IRegistry, ISaleService

logger = getLogger(__name__)


def main() -> None:
    """Main function to run the application."""

    # make sure directories exist
    config: Config = get_config()

    error_queue: IErrorQueue = ErrorQueue()
    artwork_services: IRegistry[IArtworkService] = Registry[IArtworkService]()
    order_services: IRegistry[IOrderService] = Registry[IOrderService]()
    order_services.register("Harman", HarmanOrderService.from_config(config=config))
    stock_services: IRegistry[IStockService] = Registry[IStockService]()
    stock_services.register("Harman", HarmanStockService.from_config(config=config))
    use_cases: IRegistry[IUseCase] = Registry[IUseCase]()  # type: ignore[type-arg]

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0)
    with (
        httpx.Client(
            base_url=config.odoo_base_url, follow_redirects=True, timeout=timeout
        ) as sale_engine,
        httpx.Client(
            base_url=config.spectrum_base_url, follow_redirects=True, timeout=timeout
        ) as spectrum_engine,
    ):
        spectrum_engine.headers["SPECTRUM_API_TOKEN"] = config.spectrum_api_key
        artwork_services.register(
            "Spectrum",
            SpectrumArtworkService(engine=spectrum_engine, digitals_dir=config.digitals_dir),
        )
        sale_service: ISaleService = OdooSaleService(
            auth=OdooAuth.from_config(config=config), engine=sale_engine
        )
        # use cases
        use_cases.register(
            "NewSale",
            NewSaleUseCase(
                order_services=order_services,
                artwork_services=artwork_services,
                sale_service=sale_service,
                error_queue=error_queue,
                open_orders_dir=config.open_orders_dir,
            ),
        )
        use_cases.register(
            "CompletedSale",
            CompletedSaleUseCase(
                order_services=order_services,
                sale_service=sale_service,
                error_queue=error_queue,
            ),
        )
        use_cases.register(
            "StockTransfer",
            StockTransferUseCase(
                stock_services=stock_services,
                error_queue=error_queue,
            ),
        )
        # execute use cases
        for _, use_case in use_cases.items():
            try:
                use_case.execute()
            except Exception as e:
                logger.error(f"Error executing use case {use_case.__class__.__name__}: {e!s}")


if __name__ == "__main__":
    main()
