"""Settings for the application."""

import os
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    """Settings for the application."""

    # Application settings
    templates_dir: Path = Path(__file__).parent / "templates"
    work_dir: Path = Path.home() / "projects_data" / "external_order"
    digitals_dir: Path = field(init=False)
    open_orders_dir: Path = field(init=False)

    # Harman settings
    harman_input_dir: Path = field(init=False)
    harman_output_dir: Path = field(init=False)
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_order_provider: str = "Harman INSDES"
    harman_shipment_type: str = "harman%"
    harman_workdays_for_delivery: int = 2

    # Odoo settings
    odoo_base_url: str = os.getenv("ODOO_BASE_URL", "")
    odoo_database: str = os.getenv("ODOO_DATABASE", "")
    odoo_rpc_user_id: int = int(os.getenv("ODOO_USER_ID", "0"))
    odoo_rpc_password: str = os.getenv("ODOO_PASSWORD", "")

    # Spectrum settings
    spectrum_base_url: str = os.getenv("SPECTRUM_BASE_URL", "")
    spectrum_api_key: str = os.getenv("SPECTRUM_API_KEY", "")

    def __post_init__(self):
        """Initialize settings."""
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
    """Get the application settings."""
    return Config()
