"""Application configuration for external order processing.

Loads environment variables and provides a frozen `Config` dataclass with
derived paths initialized in `__post_init__`.
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
    """Frozen `Config` dataclass holding application settings.

    Derived paths (e.g., `digitals_dir`) are set in `__post_init__`.
    """

    # Application settings
    default_box_size: tuple[int, int, int] = (24, 21, 6)  # L, W, H in cm
    digitals_dir: Path = field(init=False)
    odoo_sale_provider: str = "ODOO"
    open_orders_dir: Path = field(init=False)
    placement_file_suffix: str = "placement.pdf"
    sale_company_name: str = "Deonet Production B.V."
    ssl_verify: bool = os.getenv("SSL_VERIFY", "true").lower() == "true"
    templates_dir: Path = Path(__file__).parent / "templates"
    work_dir: Path = Path(os.getenv("WORK_DIR", Path.home() / "projects-data" / "external_order"))

    # Email settings
    smtp_host: str = os.getenv("SMTP_HOST", "smtp-relay.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_sender: str = f"External Order on {socket.gethostname()}<{os.getenv('EMAIL_SENDER', '')}>"
    email_alert_to: list[str] = field(
        default_factory=lambda: [s.strip() for s in os.getenv("EMAIL_ALERT_TO", "").split(",")]
    )
    email_stock_to: list[str] = field(
        default_factory=lambda: [s.strip() for s in os.getenv("EMAIL_STOCK_TO", "").split(",")]
    )
    email_alert_template: Path = Path(__file__).parent / "templates" / "error_alert.html"
    email_stock_template: Path = Path(__file__).parent / "templates" / "stock_email.html"

    # Camelbak settings
    camelbak_artwork_provider: str = "SPECTRUM CAMELBAK"
    camelbak_input_dir: Path = field(init=False)
    camelbak_administration_id: int = 1
    camelbak_customer_id: int = 9999999
    camelbak_pricelist_id: int = 2
    camelbak_order_provider: str = "CAMELBAK"
    camelbak_shipment_type: str = "CAMELBAK%"
    camelbak_workdays_for_delivery: int = 3

    # Harman settings
    harman_artwork_provider: str = "SPECTRUM JBL"
    # Regex patterns to distinguish B2B vs B2C orders by invoice number.
    # B2B pattern examples: 950001234, S123, S4567 (corporate/wholesale invoices)
    harman_b2b_order_filter: str = r"95000\d+|S\d+"
    # B2C pattern examples: HA-EM-123, JB-EM-ST-456, HA-EM-ST-789 (consumer/retail invoices)
    harman_b2c_order_filter: str = r"(HA|JB)-EM-(ST-)?\d+"
    harman_b2b_order_provider: str = "HARMAN JBL B2B"
    harman_b2c_order_provider: str = "HARMAN JBL B2C"
    harman_input_dir: Path = field(init=False)
    harman_output_dir: Path = field(init=False)
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_shipment_type: str = "HARMAN%"
    harman_stock_supplier_name: str = "HARMAN JBL"
    harman_stock_upload_link: str = (
        "https://drive.google.com/drive/u/0/folders/1-jWQEY9jrjKxDWNYNYsYqMqonQtZb3cD"
    )
    harman_workdays_for_delivery: int = 2

    # Log settings
    log_file: Path = field(init=False, default=Path("external_order.log"))
    log_backup_count: int = 14
    log_file_level: str = "DEBUG"

    # Odoo settings
    odoo_base_url: str = os.getenv("ODOO_BASE_URL", "")
    odoo_database: str = os.getenv("ODOO_DATABASE", "")
    odoo_rpc_user_id: int = int(os.getenv("ODOO_RPC_USER_ID", "0"))
    odoo_rpc_password: str = os.getenv("ODOO_RPC_PASSWORD", "")
    odoo_request_timeout: tuple[int, int] = (5, 30)  # (connect, read) timeout in seconds

    # Spectrum settings
    spectrum_base_url: str = os.getenv("SPECTRUM_BASE_URL", "")
    spectrum_harman_api_key: str = os.getenv("SPECTRUM_HARMAN_API_KEY", "")
    spectrum_camelbak_api_key: str = os.getenv("SPECTRUM_CAMELBAK_API_KEY", "")
    spectrum_request_timeout: tuple[int, int] = (5, 30)  # (connect, read) timeout in seconds
    spectrum_webtoprint_endpoint: str = "/api/webtoprint/"
    spectrum_order_endpoint: str = "/api/order/order-number/"
    spectrum_order_search_endpoint: str = "/api/orders/search/"
    spectrum_order_status_endpoint: str = "/api/order/status/"
    spectrum_order_shipment_endpoint: str = "/api/order/ship-notification/"

    def __post_init__(self) -> None:
        """Validate required settings and initialize derived paths."""
        # Validate required URLs are set
        required_urls = {
            "ODOO_BASE_URL": self.odoo_base_url,
            "SPECTRUM_BASE_URL": self.spectrum_base_url,
        }
        for name, url in required_urls.items():
            if not url:
                raise ValueError(f"Environment variable {name} is required but not set")

        # Set derived paths from `work_dir` and create required directories
        object.__setattr__(self, "camelbak_input_dir", self.work_dir / "camelbak" / "in")
        object.__setattr__(self, "harman_input_dir", self.work_dir / "harman" / "in")
        object.__setattr__(self, "harman_output_dir", self.work_dir / "harman" / "out")
        object.__setattr__(self, "digitals_dir", self.work_dir / "digitals")
        object.__setattr__(self, "open_orders_dir", self.work_dir / "open_orders")
        object.__setattr__(self, "log_file", self.work_dir / "logs" / self.log_file.name)

        self.camelbak_input_dir.mkdir(parents=True, exist_ok=True)
        self.harman_input_dir.mkdir(parents=True, exist_ok=True)
        self.harman_output_dir.mkdir(parents=True, exist_ok=True)
        self.digitals_dir.mkdir(parents=True, exist_ok=True)
        self.open_orders_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


@cache
def get_config() -> Config:
    """Return cached `Config` instance. Use this to access configuration."""
    return Config()
