"""Odoo authentication credentials management.

This module provides secure handling of Odoo RPC authentication credentials.
It validates all required authentication parameters and provides factory methods
for creating authenticated sessions from application configuration.
"""

from dataclasses import dataclass
from typing import Self

from src.config import Config


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooAuth:
    """Immutable container for Odoo RPC authentication credentials.

    This frozen dataclass holds the essential credentials needed to authenticate
    with an Odoo instance via XML-RPC. All fields are validated during initialization
    to ensure they meet the requirements for successful authentication.

    Attributes:
        database: The target Odoo database name. Must be a non-empty string.
        user_id: The Odoo user ID (usually an integer >= 1). Must be positive.
        password: The Odoo user password. Must be a non-empty string.

    Raises:
        ValueError: If any field fails validation during initialization.
    """

    database: str
    user_id: int
    password: str

    def __post_init__(self) -> None:
        """Validate all authentication credentials after initialization.

        Ensures:
        - Database: Non-empty, non-whitespace string
        - User ID: Positive integer (> 0)
        - Password: Non-empty, non-whitespace string

        Raises:
            ValueError: If any credential fails validation with a descriptive message.
        """
        if not (self.database and isinstance(self.database, str) and self.database.strip()):
            raise ValueError("Database cannot be empty.")
        if self.user_id <= 0:
            raise ValueError("User ID must be a positive integer.")
        if not (self.password and isinstance(self.password, str) and self.password.strip()):
            raise ValueError("Password cannot be empty.")

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create an OdooAuth instance from application configuration.

        Factory method that extracts Odoo authentication credentials from the
        application configuration object and validates them during instantiation.

        Args:
            config: Application configuration object containing Odoo credentials:
                - config.odoo_database: Target database name
                - config.odoo_rpc_user_id: User ID for RPC authentication
                - config.odoo_rpc_password: User password for RPC authentication

        Returns:
            A new OdooAuth instance with validated credentials.

        Raises:
            ValueError: If any credential from config fails validation.
        """
        return cls(
            database=config.odoo_database,
            user_id=config.odoo_rpc_user_id,
            password=config.odoo_rpc_password,
        )
