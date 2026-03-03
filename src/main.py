"""Main application orchestration and dependency injection setup.

This module serves as the application entry point, orchestrating the initialization of
all services, use cases, and their dependencies. It implements the dependency injection
pattern to wire together domain logic (use cases) with external service integrations
(Harman, Odoo, Spectrum).

The main() function performs the following orchestration:
1. Loads configuration from Config singleton
2. Initializes service registries (artwork, order, stock) with concrete implementations
3. Creates HTTP clients for Odoo and Spectrum with proper timeout configuration
4. Registers artwork service implementations (Spectrum, and Harman if needed)
5. Instantiates domain models and use cases with injected dependencies
6. Executes all registered use cases in sequence
7. Collects any exceptions that occur during execution
8. Sends error alert email if any errors were collected

Service Architecture:
- Artwork Services: Retrieve digital artwork from Spectrum and other providers
- Order Services: Read orders from Harman ERP
- Stock Services: Process stock transfers from Harman
- Sale Services: Manage sales operations in Odoo CRM
- Use Cases: Business logic orchestration (NewSale, CompletedSale, StockTransfer)

Error Handling:
All use case exceptions are caught and collected in ErrorStore, preventing one failing
use case from stopping execution of others. After all use cases complete, if ErrorStore
has collected errors, an alert email is sent to IT team with error details.

Configuration:
All external endpoint URLs, credentials, and timeouts are pulled from Config, which
loads from environment variables via .env file. This ensures no secrets are hardcoded
and supports environment-specific deployment (dev, staging, production).

Dependencies:
- src.config: Application configuration management
- src.app: Use case implementations and error handling
- src.services: External service integrations (Harman, Odoo, Spectrum)
- src.interfaces: Protocol definitions for dependency injection
"""

import socket
from logging import getLogger
from typing import TYPE_CHECKING

import httpx
from redmail.email.sender import EmailSender

from src.app.completed_sale_use_case import CompletedSaleUseCase
from src.app.errors import ErrorStore
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
from src.services.render_service import RenderService
from src.services.spectrum_artwork_service import SpectrumArtworkService

if TYPE_CHECKING:
    from src.interfaces import IRegistry, ISaleService

logger = getLogger(__name__)


def main() -> None:
    """Orchestrate application initialization, service setup, and use case execution.

    This function implements the core orchestration logic:

    Phase 1: Configuration & Error Management
    - Loads centralized Config via singleton get_config()
    - Initializes ErrorStore to collect exceptions from use cases
    - Creates service registries with dependency injection containers

    Phase 2: Service Registration
    - Registers Harman order service in order_services registry
    - Registers Harman stock service in stock_services registry
    - Creates template rendering service for email/EDI generation
    - Registers use cases (NewSale, CompletedSale, StockTransfer)

    Phase 3: HTTP Client Setup
    - Creates httpx.Client instances for Odoo and Spectrum with:
      - Connection timeout: 10 seconds (initial connection)
      - Read timeout: 120 seconds (long-running API operations)
      - Write timeout: 30 seconds (request body upload)
      - Auto follow_redirects for OAuth flows
    - Registers Spectrum artwork service with configured API authentication
    - Instantiates OdooSaleService with OAuth credentials

    Phase 4: Use Case Execution
    - Executes each registered use case in sequence:
      1. NewSale: Process new orders from Harman → create in Odoo
      2. CompletedSale: Update completed sales status in Harman
      3. StockTransfer: Process stock transfers from Harman
    - Catches and collects all exceptions in ErrorStore without interrupting

    Phase 5: Error Reporting
    - If ErrorStore has collected errors:
      1. Logs error count and severity
      2. Creates SMTP connection to Gmail relay
      3. Sends HTML email with error details to IT team
      4. Includes hostname and execution timestamp for diagnostics
    - Logs send success/failure

    Example Execution Flow:
        main()
        # Configuration loads from .env
        # Services instantiate with dependency injection
        # Use cases execute in order
        # Any raised exceptions are logged and collected
        # If errors exist, alert email is sent

    Raises:
        No exceptions are raised from main() itself. All exception handling is
        encapsulated in ErrorStore collection and error alert email sending.
        However, if EmailSender initialization or configuration loading fails
        before use case execution, those exceptions will propagate.

    Note:
        The main() function uses a context manager (with statement) to ensure
        httpx.Client instances are properly closed after all use cases complete,
        even if exceptions occur during execution.
    """

    # make sure directories exist
    config: Config = get_config()
    error_store = ErrorStore()

    artwork_services: IRegistry[IArtworkService] = Registry[IArtworkService]()
    order_services: IRegistry[IOrderService] = Registry[IOrderService]()
    order_services.register("Harman", HarmanOrderService.from_config(config=config))
    RenderService(directory=config.templates_dir)
    stock_services: IRegistry[IStockService] = Registry[IStockService]()
    stock_services.register("Harman", HarmanStockService.from_config(config=config))
    use_cases: IRegistry[IUseCase] = Registry[IUseCase]()  # type: ignore[type-arg]

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0)

    def create_client(url: str) -> httpx.Client:
        return httpx.Client(base_url=url, follow_redirects=True, timeout=timeout)

    with (
        create_client(config.odoo_base_url) as sale_engine,
        create_client(config.spectrum_base_url) as spectrum_engine,
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
                open_orders_dir=config.open_orders_dir,
            ),
        )
        use_cases.register(
            "CompletedSale",
            CompletedSaleUseCase(
                order_services=order_services,
                sale_service=sale_service,
            ),
        )
        use_cases.register(
            "StockTransfer",
            StockTransferUseCase(
                stock_services=stock_services,
            ),
        )
        # execute use cases
        for _, use_case in use_cases.items():
            try:
                use_case.execute()
            except Exception as exc:
                error_store.add(exc)
                logger.error(f"Error executing use case {use_case.__class__.__name__}: {exc!s}")

    # After all use cases have executed, check if there were any errors and send email if so
    if error_store.has_errors():
        logger.info("Errors were collected during execution, sending alert email...")
        try:
            emailer = EmailSender(host=config.smtp_host, port=config.smtp_port, use_starttls=True)
            emailer.send(
                subject=f"Deonet External Order - Errors during execution on {socket.gethostname()}",
                sender=config.email_sender,
                receivers=[config.email_alert_recipient],
                html_template="error_alert.html",
                body_params=error_store.get_render_email_data(),
            )

            logger.info("Error alert email sent successfully.")
        except Exception as exc:
            logger.error(f"Failed to send error alert email: {exc!s}")


if __name__ == "__main__":
    main()
