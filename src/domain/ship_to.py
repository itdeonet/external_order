"""Domain model for shipping addresses.

This module defines the ShipTo class, which represents a delivery address
for an order. ShipTo instances contain comprehensive contact and location
information used for fulfillment. All shipping addresses are immutable and
validated at construction time with strict requirements for required vs
optional fields.

Validation ensures:
- Required fields (remote_customer_id, contact_name, email, phone, street1, city, postal_code, country_code) are non-empty
- Optional fields (company_name, street2, state) are validated but may be empty
- Email addresses are valid and normalized to lowercase
- Phone numbers are valid and properly formatted
- Country codes are valid ISO 3166-1 alpha-2 codes
- All string fields are trimmed and normalized appropriately
"""

import uuid
from dataclasses import dataclass, field

import src.domain.validators as validators


@dataclass(frozen=True, slots=True, kw_only=True)
class ShipTo:
    """Immutable shipping address model for order fulfillment.

    A shipping address contains all necessary information to deliver an order
    to a customer. This includes contact details, street address, city, state,
    postal code, and country code. Some fields are optional (company_name,
    street2, state) to accommodate diverse international addresses.
    All fields are validated during post-initialization and are immutable
    after construction.

    This class enforces:
    - Immutability: All attributes are read-only after object creation
    - Validation: All fields must meet strict delivery requirements
    - Contact integrity: Email and phone must be valid formats
    - Address completeness: Required address fields must be present
    - Internationalization: Supports any ISO 3166-1 country code

    Attributes:
        id: Unique auto-generated UUID for this address instance
        remote_customer_id: External customer ID from source system (non-empty)
        company_name: Business name for delivery (optional, default: empty)
        contact_name: Person name for delivery (non-empty)
        email: Contact email address (must be valid email format)
        phone: Contact phone number (must be valid phone format)
        street1: Primary street address (non-empty)
        street2: Secondary address line (optional, default: empty)
        city: City name (non-empty)
        state: State/province (optional, default: empty)
        postal_code: ZIP/postal code (non-empty, normalized to uppercase)
        country_code: ISO 3166-1 alpha-2 country code (non-empty, uppercase)

    Example:
        >>> ship_to = ShipTo(
        ...     remote_customer_id="CUST123",
        ...     contact_name="John Doe",
        ...     email="john@example.com",
        ...     phone="+1-234-567-8900",
        ...     street1="123 Main St",
        ...     street2="Suite 100",
        ...     city="Springfield",
        ...     state="IL",
        ...     postal_code="62701",
        ...     country_code="us",
        ... )
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    active: bool = field(default=False, init=False)  # archived, not loaded in client portal
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
        """Validate and normalize all shipping address fields after initialization.

        This method is called automatically by the dataclass decorator after
        the instance is created. It validates each field with strict requirements
        for required fields and flexible requirements for optional fields,
        normalizing string values appropriately. All validations must pass
        before the object is considered fully initialized.

        Validation and normalization steps performed:
        1. remote_customer_id: non-empty string (trimmed)
        2. company_name: optional string (trimmed, may be empty)
        3. contact_name: non-empty string (trimmed)
        4. email: valid email format (normalized to lowercase)
        5. phone: valid phone number format (properly formatted)
        6. street1: non-empty string (trimmed)
        7. street2: optional string (trimmed, may be empty)
        8. city: non-empty string (trimmed)
        9. state: optional string (trimmed, may be empty)
        10. postal_code: non-empty string (trimmed, normalized to uppercase)
        11. country_code: valid ISO 3166-1 alpha-2 code (normalized to uppercase)

        Raises:
            ValueError: If any required field is empty or invalid
            ValueError: If email is not a valid email address
            ValueError: If phone is not a valid phone number
            ValueError: If country_code is not a valid ISO 3166-1 alpha-2 code
        """
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
