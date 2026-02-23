"""Odoo authentication module."""

from dataclasses import dataclass
from typing import Self

from src.config import Config


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooAuth:
    """Odoo authentication data."""

    database: str
    user_id: int
    password: str

    def __post_init__(self) -> None:
        if not (self.database and isinstance(self.database, str)):
            raise ValueError("Database cannot be empty.")
        if self.user_id <= 0:
            raise ValueError("User ID must be a positive integer.")
        if not (self.password and isinstance(self.password, str)):
            raise ValueError("Password cannot be empty.")

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create an OdooAuth instance from settings."""
        return cls(
            database=config.odoo_database,
            user_id=config.odoo_rpc_user_id,
            password=config.odoo_rpc_password,
        )
