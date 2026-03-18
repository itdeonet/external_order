"""Main application orchestration and dependency injection setup.

Entry point that initializes services, use cases, and dependencies, then executes
all use cases and sends error alerts if exceptions occur.
"""

import socket
from logging import getLogger

import requests
from redmail.email.sender import EmailSender

from src.app.completed_sale_use_case import CompletedSaleUseCase
from src.app.errors import get_error_store
from src.app.log_setup import configure_logging
from src.app.new_sale_use_case import NewSaleUseCase
from src.app.registry import get_use_cases
from src.app.stock_transfer_use_case import StockTransferUseCase
from src.config import Config, get_config
from src.services.harman_order_service import HarmanOrderService
from src.services.harman_stock_service import HarmanStockService
from src.services.odoo_sale_service import OdooSaleService
from src.services.spectrum_artwork_service import SpectrumArtworkService

logger = getLogger(__name__)


def main() -> None:
    """Initialize services and use cases, execute them, and send error alerts.

    Catches per-use-case exceptions without stopping execution. Sends alert email
    if any errors are collected.
    """

    config: Config = get_config()
    error_store = get_error_store()
    configure_logging(
        log_file=config.log_file,
        backup_count=config.log_backup_count,
        log_file_level=config.log_file_level,
    )
    logger.info("Application started")

    with (
        requests.Session() as odoo_session,
        requests.Session() as spectrum_harman_session,
        requests.Session() as spectrum_camelbak_session,
    ):
        # register services
        SpectrumArtworkService.register(
            name=config.harman_artwork_provider,
            session=spectrum_harman_session,
            api_key=config.spectrum_harman_api_key,
        )
        SpectrumArtworkService.register(
            name=config.camelbak_artwork_provider,
            session=spectrum_camelbak_session,
            api_key=config.spectrum_camelbak_api_key,
        )
        HarmanOrderService.register(
            name=config.harman_b2c_order_provider,
            artwork_provider=config.harman_artwork_provider,
            name_filter=config.harman_b2c_order_filter,
        )
        HarmanOrderService.register(
            name=config.harman_b2b_order_provider,
            artwork_provider="",
            name_filter=config.harman_b2b_order_filter,
        )
        HarmanStockService.register(name=config.harman_stock_supplier_name)
        # TODO: Re-enable Camelbak order service when API is available
        # SpectrumOrderService.register(
        #     name=config.camelbak_order_provider,
        #     session=spectrum_camelbak_session,
        #     api_key=config.spectrum_camelbak_api_key,
        #     artwork_provider=config.camelbak_artwork_provider,
        # )
        OdooSaleService.register(name=config.odoo_sale_provider, session=odoo_session)

        # register use cases
        NewSaleUseCase.register(name="NewSale")
        CompletedSaleUseCase.register(name="CompletedSale")
        StockTransferUseCase.register(name="StockTransfer")

        # execute use cases
        for use_case_name, use_case in get_use_cases().items():
            try:
                logger.info("Execute use case: %s", use_case_name)
                use_case.execute()
            except Exception as exc:
                error_store.add(exc)
                logger.error("Failed to execute use case %s: %s", use_case_name, exc)

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
            logger.error("Failed to send error alert email: %s", exc)

    logger.info("Application finished")
    with config.log_file.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n{'=' * 80}\n")  # add spacing in log file for next run


if __name__ == "__main__":
    main()
