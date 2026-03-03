"""Application configuration management.

This module defines the centralized configuration for the external order processing
application. It loads environment variables from .env file and aggregates application
settings across multiple systems: email, Harman ERP, Odoo, and Spectrum.

The Config class is a frozen dataclass that enforces immutability once instantiated,
ensuring configuration consistency throughout the application lifecycle. Derived attributes
(harman_input_dir, harman_output_dir, digitals_dir, open_orders_dir) are computed during
__post_init__() and the corresponding directories are created if they don't exist.

Configuration is typically accessed via the cached get_config() function, which returns
the same Config instance across the application, eliminating redundant instantiation.

Environment Variables Required:
- ODOO_BASE_URL: Base URL for Odoo JSON-RPC API
- ODOO_DATABASE: Odoo database name
- ODOO_USER_ID: Numeric user ID for Odoo authentication
- ODOO_PASSWORD: Odoo user password for authentication
- SPECTRUM_BASE_URL: Base URL for Spectrum artwork API
- SPECTRUM_API_KEY: API key for Spectrum authentication

Key Configuration Sections:
- Application: templates, working directories, default box dimensions
- Email: SMTP relay and recipient settings
- Harman: ERP integration, administration codes, and shipment logistics
- Odoo: JSON-RPC endpoint and credentials
- Spectrum: Artwork service endpoint and API authentication
"""

import os
import socket
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    """Frozen dataclass for centralized application configuration across all subsystems.

    This class aggregates configuration for Harman ERP, Odoo CRM, Spectrum artwork system,
    and email/SMTP services. The frozen dataclass pattern ensures configuration immutability
    once initialized, preventing runtime modifications that could destabilize service integrations.

    Configuration is divided into logical sections:

    Application Settings:
    - templates_dir: Path to Jinja2 templates for email and EDI rendering
    - work_dir: Base directory for all application working files
    - digitals_dir: Subdirectory for downloaded artwork files (initialized in __post_init__)
    - open_orders_dir: Subdirectory for open orders tracking (initialized in __post_init__)
    - default_box_size: Standard carton dimensions (L, W, H in cm)
    - sale_company_name: Legal company name for invoices/documents

    Email/SMTP Settings:
    - smtp_host: Gmail SMTP relay host for email delivery
    - smtp_port: SMTP server port (TLS)
    - email_sender: From address with hostname context
    - email_alert_recipient: Alert notification recipient

    Harman ERP Settings:
    - harman_input_dir: EDI order file input directory
    - harman_output_dir: EDI notification file output directory
    - harman_administration_id: Harman admin code for orders
    - harman_customer_id: Deonet's customer ID in Harman system
    - harman_pricelist_id: Default pricelist for order costing
    - harman_order_provider: EDI provider identifier
    - harman_shipment_type: Wildcard pattern for order matching
    - harman_stock_supplier_name: Supplier name for stock transfers
    - harman_stock_upload_link: Google Drive link for stock reports
    - harman_workdays_for_delivery: Lead time for Harman shipments

    Odoo Settings:
    - odoo_base_url: Odoo server base URL for JSON-RPC
    - odoo_database: Odoo database/instance name
    - odoo_rpc_user_id: Numeric user ID for API authentication
    - odoo_rpc_password: User password for JSON-RPC calls

    Spectrum Settings:
    - spectrum_base_url: Spectrum API base URL
    - spectrum_api_key: API key for authentication

    Example:
        >>> config = Config()
        >>> config.default_box_size
        (24, 21, 6)
        >>> config.harman_customer_id
        5380
        >>> config.digitals_dir.exists()
        True
        >>> config.harman_input_dir.parent == config.work_dir / "harman"
        True

    Raises:
        ValueError: If any Path initialization fails or directory creation is blocked.
    """

    # Application settings
    templates_dir: Path = Path(__file__).parent / "templates"
    work_dir: Path = Path.home() / "projects_data" / "external_order"
    digitals_dir: Path = field(init=False)
    open_orders_dir: Path = field(init=False)
    default_box_size: tuple[int, int, int] = (24, 21, 6)  # L, W, H in cm
    sale_company_name: str = "Deonet Production B.V."

    # Email settings
    smtp_host: str = "smtp-relay.gmail.com"
    smtp_port: int = 587
    email_sender: str = f"Deonet External Order on {socket.gethostname()}<no-reply@deonet.com>"
    email_alert_recipient: str = "Deonet IT Team<it@deonet.com>"

    # Harman settings
    harman_input_dir: Path = field(init=False)
    harman_output_dir: Path = field(init=False)
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_order_provider: str = "Harman INSDES"
    harman_shipment_type: str = "harman%"
    harman_stock_supplier_name: str = "Harman JBL"
    harman_stock_upload_link: str = (
        "https://drive.google.com/drive/u/0/folders/1-jWQEY9jrjKxDWNYNYsYqMqonQtZb3cD"
    )
    harman_workdays_for_delivery: int = 2

    # Odoo settings
    odoo_base_url: str = os.getenv("ODOO_BASE_URL", "")
    odoo_database: str = os.getenv("ODOO_DATABASE", "")
    odoo_rpc_user_id: int = int(os.getenv("ODOO_USER_ID", "0"))
    odoo_rpc_password: str = os.getenv("ODOO_PASSWORD", "")

    # Spectrum settings
    spectrum_base_url: str = os.getenv("SPECTRUM_BASE_URL", "")
    spectrum_api_key: str = os.getenv("SPECTRUM_API_KEY", "")

    def __post_init__(self) -> None:
        """Initialize derived path attributes and create required directories.

        Computes the absolute paths for Harman and order management directories based
        on the work_dir base path, then creates all directories if they don't exist.
        Uses object.__setattr__() to bypass frozen dataclass constraints for field-init=False
        attributes.

        Derived Attributes (computed from work_dir):
        - harman_input_dir: {work_dir}/harman/in - EDIFACT order file input
        - harman_output_dir: {work_dir}/harman/out - EDIFACT notification output
        - digitals_dir: {work_dir}/digitals - Downloaded artwork files
        - open_orders_dir: {work_dir}/open_orders - Order tracking

        Directory Creation:
        All derived paths are created with parents=True and exist_ok=True, allowing
        safe initialization even if directories already exist. This is called automatically
        during Config() instantiation.

        Raises:
            OSError: If directory creation fails due to permissions, invalid paths,
                    or other filesystem errors (e.g., work_dir on non-existent mount).

        Example:
            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmpdir:
            ...     config = Config()
            ...     object.__setattr__(config, "work_dir", Path(tmpdir))
            ...     config.__post_init__()
            ...     config.digitals_dir.exists()
            True
        """
        object.__setattr__(self, "harman_input_dir", self.work_dir / "harman" / "in")
        object.__setattr__(self, "harman_output_dir", self.work_dir / "harman" / "out")
        object.__setattr__(self, "digitals_dir", self.work_dir / "digitals")
        object.__setattr__(self, "open_orders_dir", self.work_dir / "open_orders")

        self.harman_input_dir.mkdir(parents=True, exist_ok=True)
        self.harman_output_dir.mkdir(parents=True, exist_ok=True)
        self.digitals_dir.mkdir(parents=True, exist_ok=True)
        self.open_orders_dir.mkdir(parents=True, exist_ok=True)


@cache
def get_config() -> Config:
    """Get cached application configuration instance.

    Returns the same Config instance across all function calls within the application
    lifecycle. The @cache decorator (functools.cache) creates a singleton pattern,
    eliminating redundant Config instantiation and ensuring consistent configuration
    throughout the application.

    This function should be the primary entry point for accessing configuration rather
    than directly instantiating Config(), as it prevents multiple __post_init__() calls
    and directory creation operations.

    Returns:
        Config: Cached frozen dataclass instance with all paths initialized and
               directories created. The same instance is returned on all subsequent calls.

    Example:
        >>> config1 = get_config()
        >>> config2 = get_config()
        >>> config1 is config2  # Same instance (cached)
        True
        >>> config1.odoo_base_url == config2.odoo_base_url
        True

    Note:
        The cache is application-wide and cleared only when the Python process terminates.
        Changes to .env file after first get_config() call will NOT be reflected; restart
        the application to reload configuration from environment.
    """
    return Config()
