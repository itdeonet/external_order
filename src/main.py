"""Main entry point for the application."""

from logging import getLogger
from typing import TYPE_CHECKING

import httpx

from app.new_sale_use_case import NewSaleUseCase
from src.app.errors import ErrorQueue
from src.app.odoo_auth import OdooAuth
from src.app.registry import Registry
from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.interfaces.iorder_service import IOrderService
from src.services.harman_order_service import HarmanOrderService
from src.services.odoo_sales_service import OdooSalesService
from src.services.spectrum_artwork_service import SpectrumArtworkService
from src.settings import Settings, get_settings

if TYPE_CHECKING:
    from src.domain.interfaces.ierror_queue import IErrorQueue
    from src.domain.interfaces.iregistry import IRegistry
    from src.domain.interfaces.isales_service import ISalesService

logger = getLogger(__name__)


def main() -> None:
    """Main function to run the application."""

    # make sure directories exist
    settings: Settings = get_settings()

    error_queue: IErrorQueue = ErrorQueue()
    artwork_services: IRegistry[IArtworkService] = Registry[IArtworkService]()
    order_services: IRegistry[IOrderService] = Registry[IOrderService]()
    order_services.register("Harman", HarmanOrderService.from_settings(settings))

    timeout = httpx.Timeout(connect=10.0, read=1200.0, write=30.0)
    with (
        httpx.Client(
            base_url=settings.odoo_base_url,
            follow_redirects=True,
            timeout=timeout,
        ) as sale_engine,
        httpx.Client(
            base_url=settings.spectrum_base_url,
            follow_redirects=True,
            timeout=timeout,
            headers={"SPECTRUM_API_TOKEN": settings.spectrum_api_key},
        ) as spectrum_engine,
    ):
        artwork_services.register(
            "Spectrum",
            SpectrumArtworkService(engine=spectrum_engine, digitals_dir=settings.digitals_dir),
        )
        sales_service: ISalesService = OdooSalesService(
            auth=OdooAuth.from_settings(settings=settings), engine=sale_engine
        )
        # use cases
        NewSaleUseCase(
            order_services=order_services,
            artwork_services=artwork_services,
            sales_service=sales_service,
            error_queue=error_queue,
            open_orders_dir=settings.open_orders_dir,
        ).create_sales()


if __name__ == "__main__":
    main()
