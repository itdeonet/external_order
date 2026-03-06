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
    templates_dir: Path = Path(__file__).parent / "templates"
    work_dir: Path = Path(os.getenv("WORK_DIR", Path.home() / "projects_data" / "external_order"))
    digitals_dir: Path = field(init=False)
    open_orders_dir: Path = field(init=False)
    default_box_size: tuple[int, int, int] = (24, 21, 6)  # L, W, H in cm
    sale_company_name: str = "Deonet Production B.V."
    ssl_verify: bool = os.getenv("SSL_VERIFY", "true").lower() == "true"

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

    # Harman settings
    harman_input_dir: Path = field(init=False)
    harman_output_dir: Path = field(init=False)
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_order_provider: str = "HARMAN JBL"
    harman_shipment_type: str = "harman%"
    harman_stock_supplier_name: str = "Harman JBL"
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

    # Spectrum settings
    spectrum_base_url: str = os.getenv("SPECTRUM_BASE_URL", "")
    spectrum_api_key: str = os.getenv("SPECTRUM_API_KEY", "")

    def __post_init__(self) -> None:
        """Set derived paths from `work_dir` and create required directories."""
        object.__setattr__(self, "harman_input_dir", self.work_dir / "harman" / "in")
        object.__setattr__(self, "harman_output_dir", self.work_dir / "harman" / "out")
        object.__setattr__(self, "digitals_dir", self.work_dir / "digitals")
        object.__setattr__(self, "open_orders_dir", self.work_dir / "open_orders")
        object.__setattr__(self, "log_file", self.work_dir / "logs" / self.log_file.name)

        self.harman_input_dir.mkdir(parents=True, exist_ok=True)
        self.harman_output_dir.mkdir(parents=True, exist_ok=True)
        self.digitals_dir.mkdir(parents=True, exist_ok=True)
        self.open_orders_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


@cache
def get_config() -> Config:
    """Return cached `Config` instance. Use this to access configuration."""
    return Config()
