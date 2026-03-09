"""Shipping address model.

Defines `ShipTo`, an immutable, validated shipping address for orders.
"""

from dataclasses import dataclass

import src.domain.validators as validators


@dataclass(frozen=True, slots=True, kw_only=True)
class ShipTo:
    """Immutable shipping address.

    Validates required fields and normalizes contact data.
    """

    remote_customer_id: str
    company_name: str = ""
    contact_name: str
    email: str
    phone: str
    street1: str
    street2: str = ""
    city: str
    state: str = ""
    postal_code: str
    country_code: str

    def __post_init__(self) -> None:
        """Validate and normalize fields; raise ValueError on invalid input."""
        validators.validate_non_empty_string(self.remote_customer_id, "Remote customer ID")
        validators.set_normalized_string(self, "remote_customer_id", self.remote_customer_id)

        # company_name is optional
        company_normalized = validators.validate_optional_string(self.company_name, "Company name")
        object.__setattr__(self, "company_name", company_normalized)

        validators.validate_non_empty_string(self.contact_name, "Contact name")
        validators.set_normalized_string(self, "contact_name", self.contact_name)

        # email validation and normalization (lowercase)
        email = validators.validate_email(self.email)
        object.__setattr__(self, "email", email)

        # phone validation and normalization
        phone = validators.validate_phone(self.phone)
        object.__setattr__(self, "phone", phone)

        validators.validate_non_empty_string(self.street1, "Street1")
        validators.set_normalized_string(self, "street1", self.street1)

        # street2 is optional
        street2_normalized = validators.validate_optional_string(self.street2, "Street2")
        object.__setattr__(self, "street2", street2_normalized)

        validators.validate_non_empty_string(self.city, "City")
        validators.set_normalized_string(self, "city", self.city)

        # state is optional
        state_normalized = validators.validate_optional_string(self.state, "State")
        object.__setattr__(self, "state", state_normalized)

        validators.validate_non_empty_string(self.postal_code, "Postal code")
        validators.set_normalized_string(self, "postal_code", self.postal_code, transform="upper")

        # country_code with uppercase normalization (validation done in validator)
        country_code = validators.validate_country_code(self.country_code)
        object.__setattr__(self, "country_code", country_code)
