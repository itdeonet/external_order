"""Main application orchestration and dependency injection setup.

Entry point that initializes services, use cases, and dependencies, then executes
all use cases and sends error alerts if exceptions occur.
"""

import socket
from logging import getLogger
from typing import TYPE_CHECKING

import requests
from redmail.email.sender import EmailSender

from src.app.completed_sale_use_case import CompletedSaleUseCase
from src.app.errors import get_error_store
from src.app.log_setup import configure_logging
from src.app.new_sale_use_case import NewSaleUseCase
from src.app.registry import Registry
from src.app.stock_transfer_use_case import StockTransferUseCase
from src.config import Config, get_config
from src.domain import (
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
    from src.domain import IRegistry, ISaleService

logger = getLogger(__name__)


def main() -> None:
    """Initialize services and use cases, execute them, and send error alerts.

    Catches per-use-case exceptions without stopping execution. Sends alert email
    if any errors are collected.
    """

    # make sure directories exist
    config: Config = get_config()
    error_store = get_error_store()
    configure_logging(
        log_file=config.log_file,
        backup_count=config.log_backup_count,
        log_file_level=config.log_file_level,
    )
    logger.info("Application started")

    artwork_services: IRegistry[IArtworkService] = Registry[IArtworkService]()
    order_services: IRegistry[IOrderService] = Registry[IOrderService]()
    order_services.register(config.harman_order_provider, HarmanOrderService())
    stock_services: IRegistry[IStockService] = Registry[IStockService]()
    stock_services.register(config.harman_stock_supplier_name, HarmanStockService())
    use_cases: IRegistry[IUseCase] = Registry[IUseCase]()  # type: ignore[type-arg]

    with (
        requests.Session() as sale_session,
        requests.Session() as spectrum_session,
    ):
        artwork_services.register("Spectrum", SpectrumArtworkService(session=spectrum_session))
        sale_service: ISaleService = OdooSaleService(session=sale_session)
        # use cases
        use_cases.register(
            "NewSale",
            NewSaleUseCase(
                order_services=order_services,
                artwork_services=artwork_services,
                sale_service=sale_service,
                open_orders_dir=config.open_orders_dir,
            ),
        )
        use_cases.register(
            "CompletedSale",
            CompletedSaleUseCase(order_services=order_services, sale_service=sale_service),
        )
        use_cases.register(
            "StockTransfer",
            StockTransferUseCase(stock_services=stock_services),
        )
        # execute use cases
        for use_case_name, use_case in use_cases.items():
            try:
                logger.info(f"Execute use case: {use_case_name}")
                use_case.execute()
            except Exception as exc:
                error_store.add(exc)
                logger.error(f"Failed to execute use case {use_case_name}: {exc!s}")

    # After all use cases have executed, check if there were any errors and send email if so
    if error_store.has_errors():
        logger.info("Errors were collected during execution, sending alert email...")
        try:
            emailer = EmailSender(host=config.smtp_host, port=config.smtp_port, use_starttls=True)
            emailer.set_template_paths(config.templates_dir)
            emailer.send(
                subject=f"Deonet External Order - Errors during execution on {socket.gethostname()}",
                sender=config.email_sender,
                receivers=config.email_alert_to,
                html_template=config.email_alert_template.name,
                body_params=error_store.get_render_email_data(),
            )

            logger.info("Error alert email sent successfully.")
        except Exception as exc:
            logger.error(f"Failed to send error alert email: {exc!s}")

    logger.info("Application finished")
    with config.log_file.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n{'=' * 80}\n")  # add spacing in log file for next run


if __name__ == "__main__":
    main()
