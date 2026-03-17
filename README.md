# Deonet External Order Synchronization

A modular order synchronization system that imports orders from external providers, creates sales in Odoo, manages artwork workflows, and handles stock transfers. Built with Python 3.12+ using clean architecture principles.

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Architecture](#architecture)
- [Setup and Installation](#setup-and-installation)
- [Configuration](#configuration)
- [Domain Entities](#domain-entities)
- [Adding New Services](#adding-new-services)
- [Testing](#testing)
- [Error Handling](#error-handling)
- [Development Workflow](#development-workflow)
- [Dependencies](#dependencies)

## Overview

This application orchestrates a multi-step workflow for processing external orders:

1. **Read Orders** - Import order data from external providers (currently Harman, extensible to others)
2. **Create Sales** - Create corresponding sales in Odoo ERP system
3. **Manage Artwork** - Fetch and manage product artwork from external services (Spectrum)
4. **Confirm Sales** - Complete the sales workflow in Odoo
5. **Stock Transfers** - Handle inventory movements between warehouse systems
6. **Notifications** - Send delivery notifications (EDIFACT format)

The system is designed as a **pluggable service architecture** where new order providers, artwork services, and stock systems can be added without modifying core logic.

## File Structure

```
deonet-external-order/
├── src/                           # Application source code
│   ├── app/                       # Application layer (use cases)
│   │   ├── completed_sale_use_case.py      # Process completed sales
│   │   ├── new_sale_use_case.py            # Create new sales workflow
│   │   ├── stock_transfer_use_case.py      # Handle stock transfers
│   │   ├── odoo_auth.py                    # Odoo authentication
│   │   ├── registry.py                     # Service registry (plugin pattern)
│   │   └── errors.py                       # Custom exception types & ErrorStore
│   │
│   ├── domain/                    # Domain layer (business entities)
│   │   ├── order.py               # Order aggregate root
│   │   ├── line_item.py           # Order line item
│   │   ├── ship_to.py             # Shipping address
│   │   ├── artwork.py             # Artwork metadata
│   │   └── validators.py          # Domain validation rules
│   │
│   ├── services/                  # Infrastructure layer (external integrations)
│   │   ├── harman_order_service.py         # Harman order provider
│   │   ├── harman_stock_service.py         # Harman stock transfers
│   │   ├── odoo_sale_service.py            # Odoo ERP integration
│   │   ├── spectrum_artwork_service.py     # Spectrum artwork provider
│   │   └── render_service.py               # Jinja2 template rendering
│   │
│   ├── interfaces/                # Interface contracts (protocols)
│   │   ├── base.py                # All interface definitions
│   │   └── __init__.py            # Interface exports
│   │
│   ├── templates/                 # Jinja2 templates
│   │   ├── desadvd96a.j2          # EDIFACT D96A delivery notification
│   │   └── desadvd99a.j2          # EDIFACT D99A delivery notification
│   │
│   ├── config.py                  # Configuration management
│   └── main.py                    # Application entry point
│
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests (100+ tests)
│   │   ├── app/                   # Use case tests
│   │   ├── domain/                # Entity and validator tests
│   │   └── services/              # Service integration tests
│   │
│   └── integration/               # Integration tests
│       └── test_main.py           # Main setup tests
│
├── pyproject.toml                 # Project configuration & dependencies
├── README.md                      # This file
└── .env.example                   # Example environment variables
```

**Key Directories:**

- **`src/app/`** - Use cases & application orchestration (no business logic, pure coordination)
- **`src/domain/`** - Pure business logic & validation rules (framework-agnostic)
- **`src/services/`** - External system integrations & HTTP clients
- **`src/interfaces/`** - Protocol definitions (TypeScript-like interfaces for Python)

## Architecture

### High-Level Data Flow

**New Sales Workflow:**
```
External Order Provider (Harman/others)
        ↓
    Read Orders [IOrderService.read_orders()]
        ↓
  Create or Update Sale in Odoo [ISaleService]
        ↓
  Get Artwork (if service exists) [IOrderService.get_artwork_service()]
        ↓
  Fetch Artwork [IArtworkService.get_artwork()]
        ↓
  Persist Order as CONFIRMED
```

**Completed Sales Workflow:**
```
Odoo Completed Sales
        ↓
  Get Notify Data [IOrderService.get_notify_data()]
        ↓
  Send EDIFACT Notification [IOrderService.notify_completed_sale()]
        ↓
  Mark Sale Notified [ISaleService.mark_sale_notified()]
        ↓
  Persist Order as COMPLETED
```

**Stock Transfer Workflow:**
```
Harman Stock Transfer Requests (XML)
        ↓
  Read Transfers [IStockService.read_stock_transfers()]
        ↓
  Create Reply [IStockService.create_stock_transfer_reply()]
        ↓
  Email Reply [IStockService.email_stock_transfer_reply()]
        ↓
  Mark Processed [IStockService.mark_transfer_as_processed()]
```

### Core Design Patterns

#### 1. **Service Registry (Plugin Architecture)**

Services are registered at runtime, allowing new providers to be plugged in without code changes:

```python
# In main.py
order_services: IRegistry[IOrderService] = Registry[IOrderService]()
order_services.register("Harman", HarmanOrderService.from_config(config))
order_services.register("MyNewProvider", MyNewOrderService.from_config(config))

# In use cases, iterate over all registered services
for order_service_name, order_service in order_services.items():
    for order in order_service.read_orders():
        # Process order
```

#### 2. **Protocol-Based Interfaces**

Services implement Python Protocol interfaces (like TypeScript interfaces). Each protocol defines a specific capability:

- `IOrderReader` - Read orders from a provider
- `IOrderStore` - Persist order state
- `IOrderNotifier` - Send notifications
- `IArtworkServiceProvider` - Select artwork service for order
- `IOrderService` - Full-featured order provider (combines all above)
- `ISaleService` - Create and manage sales in Odoo
- `IArtworkService` - Retrieve artwork from a provider
- `IStockService` - Handle stock transfers (read transfers, create replies, email replies, mark as processed)

Note: Error handling uses a singleton `ErrorStore` class, not an interface, to centralize error collection across all operations.

#### 3. **Separation of Concerns**

- **App Layer** - Orchestration & workflow (use cases)
- **Domain Layer** - Business rules & validation (order, line items, etc.)
- **Service Layer** - External system integration (Odoo, Harman, Spectrum)
- **Interface Layer** - Contracts between layers (protocols)

#### 4. **Error Store Pattern**

Instead of throwing exceptions up the call stack, errors are collected in a singleton ErrorStore for centralized handling:

```python
from src.app.errors import get_error_store

# Get cached instance
error_store = get_error_store()

for order in order_service.read_orders():
    try:
        # Process order
    except Exception as exc:
        error_store.add(exc)
        logger.error(f"Error processing order: {exc!s}")

# Summarize all errors at the end
if error_store.has_errors():
    logger.error(error_store.summarize())
```

### Use Cases (Application Workflows)

#### **NewSaleUseCase**
Workflow: Read Orders → Create/Update Sales → Get Artwork (conditional) → Confirm Sales

```python
NewSaleUseCase.execute():
  """Process new orders from all registered order services."""
  for each order_service in order_services.items():
    for each order in order_service.read_orders():
      try:
        # 1. Persist order as NEW
        order_service.persist_order(order, OrderStatus.NEW)
        
        # 2. Create or update sale in Odoo
        sale_id, sale_name = sale_service.create_sale(order)  # Returns tuple
        order.set_sale_id(sale_id)
        order.set_sale_name(sale_name)  # Store sale name from Odoo
        
        # 3. Get artwork if service available
        artwork_service = order_service.get_artwork_service(order, artwork_services)
        if artwork_service:
          artwork_list = artwork_service.get_artwork(order)
          for artwork in artwork_list:
            line_item.set_artwork(artwork)  # Attach artwork to line items
          order_service.persist_order(order, OrderStatus.ARTWORK)
        
        # 4. Persist as CONFIRMED (no separate confirm step)
        order.set_status(OrderStatus.CONFIRMED)
        order_service.persist_order(order, OrderStatus.CONFIRMED)
        
      except Exception as exc:
        error_store.add(exc)  # Collect error, continue with next order
```

**Key Behavior:**
- Each order service is a registered plugin (Harman, etc.)
- `create_sale()` returns a tuple `(sale_id, sale_name)` - both must be set on order
- Artwork workflow is conditional - if `get_artwork_service()` returns None, artwork step is skipped
- Sale is created in final "sale" state in Odoo (no separate confirm step needed)
- OrderStatus transitions: NEW → ARTWORK (if artwork available) → CONFIRMED
- Errors are collected per-order; one order failure doesn't stop others

#### **SpectrumArtworkService** (Reference Implementation)

Retrieves and manages digital artwork from Spectrum REST API. Handles design downloads, placement file organization, and client authentication.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class SpectrumArtworkService:
  """Get artwork from Spectrum API."""
  session: requests.Session         # HTTP client
  api_key: InitVar[str]             # API authentication key
  session: requests.Session         # HTTP client
  api_key: InitVar[str]             # API authentication key
  base_url: str                     # Spectrum API base URL
  digitals_dir: Path                # Local directory to store downloads
  client_handle: str = field(init=False)  # Set during __post_init__
  order_data: dict = field(init=False)    # Cached from API
  
  def __post_init__(self, api_key: str) -> None:
  def __post_init__(self, api_key: str) -> None:
    """Initialize API session and fetch order metadata."""
    # Configure session headers with authorization token
    self.session.headers.update({"SPECTRUM_API_TOKEN": api_key})
    # Configure session headers with authorization token
    self.session.headers.update({"SPECTRUM_API_TOKEN": api_key})
    response = self.session.get(f"{self.base_url}/order_data")
    order_data = response.json()
    object.__setattr__(self, "order_data", order_data)
    object.__setattr__(self, "client_handle", order_data["client_handle"])
  
  def get_artwork(self, order: Order) -> list[Artwork]:
    """Fetch artwork for all line items in order.
    
    Args:
      order: Order with order_id and sale_name set
    
    Returns:
      List of Artwork objects with validated file paths
    Raises:
      ArtworkError: If order data missing or download fails
    """
    artwork_list = []
    for line_item in order.line_items:
      recipe_set_id = line_item.product_code  # Maps to recipe set in Spectrum API
      designs = self._download_designs(recipe_set_id, order.sale_name)
      for design in designs:
        placement_path = self._download_placement(recipe_set_id, order.sale_name)
        artwork = Artwork(
            product_code=line_item.product_code,
            material=design["material"],
            file_path=placement_path,
        )
        artwork_list.append(artwork)
    return artwork_list
        artwork_list.append(artwork)
    return artwork_list
```

**Key Design Patterns:**
- **Frozen Dataclass** - Immutable after initialization
- **init=False Fields** - Changed via `object.__setattr__()` in `__post_init__()`
- **Single-responsibility Methods** - Each private method handles one task
- **Validation** - Artwork objects validate file existence on creation
- **Error Handling** - Raises ArtworkError with context; caller uses ErrorStore

#### **CompletedSaleUseCase**
Workflow: Find Completed Sales → Get Notification Data → Send Notifications → Mark Notified

```python
CompletedSaleUseCase.execute():
  """Process completed sales from Odoo."""
  for each order_service in order_services.items():
    for sale_id, remote_order_id in sale_service.search_completed_sales(provider):
      try:
        # 1. Load order from provider cache
        order = order_service.load_order(remote_order_id)
        if not order:
          raise SaleError(f"Order not found: {remote_order_id}")
        
        # 2. Get data needed for notification
        notify_data = order_service.get_notify_data(order, sale_service)
        
        # 3. Send EDIFACT notification (D96A + D99A formats)
        order_service.notify_completed_sale(order, notify_data)
        
        # 4. Mark sale as notified
        sale_service.mark_sale_notified(sale_id)
        
        # 5. Persist order as COMPLETED
        order.set_status(OrderStatus.COMPLETED)
        order_service.persist_order(order, OrderStatus.COMPLETED)
        
      except Exception as exc:
        error_store.add(exc)  # Collect error, continue with next sale
```

**Key Behavior:**
- `get_notify_data()` gathers order details, shipping info, and serials from sale service
- `notify_completed_sale()` generates EDIFACT D96A and D99A messages and writes to output directory
- `mark_sale_notified()` updates Odoo flag; called only if notification succeeds
- If notification fails, mark_sale_notified is NOT called (state consistency)
- If persist fails, mark_sale_notified was already called (no rollback)

#### **StockTransferUseCase**
Workflow: Read Stock Requests → Create Reply → Email Reply → Mark as Processed

```python
StockTransferUseCase.execute():
  """Process stock transfer requests from providers."""
  for each stock_service in stock_services.items():
    for each transfer in stock_service.read_stock_transfers():
      try:
        # 1. Create reply file for the stock transfer
        reply_path = stock_service.create_stock_transfer_reply(transfer)
        
        # 2. Email the reply
        stock_service.email_stock_transfer_reply(reply_path, transfer)
        
        # 3. Mark transfer as processed (rename input file)
        stock_service.mark_transfer_as_processed(transfer)
        
      except Exception as exc:
        error_store.add(exc)  # Collect error, continue with next transfer
```

**Key Behavior:**
- Stock services implement `IStockService` with three separate operations (SOLID principle)
- `create_stock_transfer_reply()` - Creates XML reply file and returns its Path
- `email_stock_transfer_reply()` - Sends the reply file as an email attachment
- `mark_transfer_as_processed()` - Renames input file to mark as processed
- Currently HarmanStockService handles XML-based IDOC requests
- Errors are collected per-transfer; one failure doesn't block others
- If any step fails, the transfer remains unprocessed (input file not renamed)

## Setup and Installation

### Prerequisites

- **Python 3.12+** (check with `python --version`)
- **uv** package manager ([install from](https://docs.astral.sh/uv/))
- **sale_order required fields**: x_remote_delivery_instructions (char), x_remote_notified_completion (bool), x_remote_order_id (char), x_remote_order_provider (char)
- **sale_order sql update**: update sale_order set x_remote_order_provider = 'HARMAN JBL' where x_remote_order_provider = 'Harman INSDES';
- **res_partner required fields**: x_remote_order_id (char), x_remote_order_provider (char)
- **res_partner sql update**: update res_partner set active=false, portal_visible=false, x_remote_order_provider = 'HARMAN JBL' where x_remote_order_provider = 'Harman INSDES';
- **mail_followers sql insert**: INSERT INTO mail_followers (res_model, res_id, partner_id)
SELECT 'sale.order', so.id, p.id
FROM (SELECT id FROM sale_order WHERE x_remote_source = 'Harman INSDES') so
CROSS JOIN (SELECT id FROM res_partner WHERE id IN (3, 5380)) p
WHERE NOT EXISTS (
    SELECT 1 FROM mail_followers f 
    WHERE f.res_model = 'sale.order' 
    AND f.res_id = so.id 
    AND f.partner_id = p.id
);

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd deonet-external-order
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your actual credentials and settings
   nano .env  # or use your favorite editor
   ```
   
   See [Configuration](#configuration) section below for detailed variable descriptions.

4. **Verify installation**
   ```bash
   uv run pytest tests/ -q
   # Should show tests passing (80+ core tests)
   ```

### Development Setup

For active development with type checking:

```bash
# Install dev dependencies
uv sync --group dev

# Run tests with coverage
uv run pytest tests/ --cov=src

# Run type checking (if using pyright/mypy)
uv run pyright src/
```

## Configuration

Configuration is centralized in `src/config.py` and loaded from environment variables via `.env` file.

### Using `.env.example`

The repository includes a `.env.example` template file with all required and optional environment variables documented:

```bash
# Copy the template to create your local configuration
cp .env.example .env

# Edit with your actual values (credentials, URLs, API keys)
# .env is in .gitignore and should never be committed
```

**Key Points:**
- `.env.example` documents every variable with explanatory comments
- Variables marked **(Required)** must be set for the application to run
- Variables marked **(Optional)** have sensible defaults if omitted
- Never commit the actual `.env` file (it contains secrets)
- `.env` is automatically loaded on application startup via `src/config.py`

### Configuration File: `config.py`

```python
@dataclass(frozen=True, slots=True)
class Config:
    # Directories
    work_dir: Path = Path.home() / "projects-data" / "external_order"
    templates_dir: Path                          # Auto-set to src/templates
    harman_input_dir: Path                       # Auto-set from work_dir
    harman_output_dir: Path
    digitals_dir: Path
    open_orders_dir: Path
    
    # Harman settings
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_order_provider: str = "HARMAN JBL"
    harman_shipment_type: str = "harman%"
    harman_workdays_for_delivery: int = 2
    
    # Odoo settings
    odoo_base_url: str                           # from env ODOO_BASE_URL
    odoo_database: str                           # from env ODOO_DATABASE
    odoo_rpc_user_id: int                        # from env ODOO_RPC_USER_ID
    odoo_rpc_password: str                       # from env ODOO_RPC_PASSWORD
    
    # Spectrum settings
    spectrum_base_url: str                       # from env SPECTRUM_BASE_URL
    spectrum_harman_api_key: str                        # from env SPECTRUM_HARMAN_API_KEY
```

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Working Directory (optional, defaults to ~/projects-data/external_order)
WORK_DIR=/path/to/work/directory

# SSL Verification (optional, defaults to true for production)
SSL_VERIFY=true

# Email/SMTP Settings (optional, for notifications and alerts)
SMTP_HOST=smtp-relay.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your_email@company.com
EMAIL_ALERT_TO=alert@company.com
EMAIL_STOCK_TO=stock@company.com

# Odoo ERP (required for sales operations)
ODOO_BASE_URL=https://odoo.company.com
ODOO_DATABASE=production_db
ODOO_RPC_USER_ID=2
ODOO_RPC_PASSWORD=your_odoo_token_here

# Spectrum Artwork Service (required for artwork retrieval)
SPECTRUM_BASE_URL=https://staging.spectrumcustomizer.com/
SPECTRUM_HARMAN_API_KEY=your_spectrum_token_here
```

**Environment Variable Reference:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORK_DIR` | No | `~/projects-data/external_order` | Base directory for working files, logs, and order tracking |
| `SSL_VERIFY` | No | `true` | Enable/disable SSL certificate verification for HTTPS requests |
| `SMTP_HOST` | No | `smtp-relay.gmail.com` | SMTP server host for email notifications |
| `SMTP_PORT` | No | `587` | SMTP server port (TLS) |
| `EMAIL_SENDER` | No | Empty | Sender email address for notifications |
| `EMAIL_ALERT_TO` | No | Empty | Comma-separated email addresses for alerts |
| `EMAIL_STOCK_TO` | No | Empty | Comma-separated email addresses for stock transfer notifications |
| `ODOO_BASE_URL` | Yes | Empty | Base URL for Odoo JSON-RPC API |
| `ODOO_DATABASE` | Yes | Empty | Odoo database/instance name |
| `ODOO_RPC_USER_ID` | Yes | `0` | Numeric user ID for Odoo JSON-RPC API authentication |
| `ODOO_RPC_PASSWORD` | Yes | Empty | Odoo user password for JSON-RPC API authentication |
| `SPECTRUM_BASE_URL` | Yes | Empty | Base URL for Spectrum artwork API |
| `SPECTRUM_HARMAN_API_KEY` | Yes | Empty | API key for Spectrum authentication |

### Using Configuration

```python
from src.config import get_config

# Get singleton config instance (cached)
config = get_config()

# Access settings
harman_input = config.harman_input_dir
odoo_url = config.odoo_base_url
```

## Domain Entities

### Order (Aggregate Root)

The `Order` class represents a single order from an external provider:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    # Required input fields
    administration_id: int           # Provider administration ID
    customer_id: int                 # Customer/distributor ID  
    order_provider: str              # "Harman", etc. (provider name)
    pricelist_id: int                # Price list ID
    remote_order_id: str             # ID in external system
    shipment_type: str               # Shipping method/type
    description: str                 # Order description/summary
    ship_to: ShipTo                  # Shipping address object
    line_items: list[LineItem]       # Order lines with products
    
    # Optional fields
    delivery_instructions: str = ""  # Optional delivery instructions
    
    # Auto-generated read-only fields (cannot be set via __init__)
    id: int = field(init=False, default_factory=...)          # UUID-like identifier
    sale_id: int = field(init=False, default=0)               # Odoo sale ID (once created)
    status: OrderStatus = field(init=False, default=OrderStatus.NEW)  # Current status
    created_at: str = field(init=False, default_factory=...)  # ISO format datetime
    ship_at: str = field(init=False, default_factory=...)     # ISO format date (7 days ahead)

# Instance methods for setting read-only fields:
# - set_sale_id(value: int) -> None
# - set_status(value: OrderStatus) -> None
# - set_created_at(value: datetime) -> None
# - set_ship_at(value: date) -> None
```

**OrderStatus enum:**
```
NEW → CREATED → ARTWORK → CONFIRMED → COMPLETED → SHIPPED
                                            ↓
                                    FAILED (error state)
```

### ShipTo (Value Object)

Represents shipping/billing address with validation:

```python
@dataclass(frozen=True, slots=True)
class ShipTo:
    # Required fields
    remote_customer_id: str          # ID in external system
    company_name: str                # Company name (can be empty for B2C)
    contact_name: str                # Contact person (validated: non-empty)
    email: str                       # Email (validated: contains @ and .)
    phone: str                       # Phone number (basic format validation)
    street1: str                     # Primary street address
    city: str                        # City name
    postal_code: str                 # ZIP/postal code
    country_code: str                # Validated: 2-letter ISO code (e.g., "US")
    
    # Optional fields  
    street2: str = ""                # Secondary street (apt, suite, etc.)
    state_code: str = ""             # State/province code
```

### LineItem (Value Object)

Represents a single product line in an order:

```python
@dataclass(frozen=True, slots=True)
class LineItem:
    # Required fields
    line_id: str                     # Line item ID (from provider, validated: non-empty)
    product_code: str                # Product/SKU code (validated: non-empty)
    quantity: int                    # Quantity (validated: positive integer > 0)
    
    # Optional fields
    artwork: Artwork | None = None   # Product artwork (can be set via set_artwork())

# Instance method:
# - set_artwork(value: Artwork) -> None  (validates and sets artwork)
```

### Artwork (Value Object)

Represents product artwork file and metadata:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Artwork:
    # Required fields
    artwork_id: str                  # Artwork identifier (non-empty, validated)
    artwork_line_id: str             # Associated line item ID (non-empty, validated)
    design_paths: list[Path]         # List of paths to design files (must exist)
    
    # Auto-generated fields
    created_at: str = field(init=False, default_factory=...)  # ISO format datetime
```

**Validation Rules:**
- `artwork_id` and `artwork_line_id` must be non-empty strings
- `design_paths` must be a non-empty list of existing Path objects
- File existence is validated in `__post_init__()` and raises ValueError if missing
- All fields are immutable after creation (frozen dataclass)

### Built-in Validators

Every domain object is validated on creation. Core validators in `src/domain/validators.py`:

```python
# String validation
validate_email(value, field_name)              # Email format (@ and .)
validate_phone(value, field_name)              # Basic phone format
validate_country_code(value, field_name)       # 2-letter ISO code
validate_non_empty_string(value, field_name)   # Non-empty string
validate_non_empty_string_lowercase(value, field_name)  # Non-empty, lowercase
validate_non_empty_string_uppercase(value, field_name)  # Non-empty, uppercase

# Integer validation
validate_positive_int(value, field_name)       # > 0
validate_non_negative_int(value, field_name)   # >= 0

# Collection validation
validate_list_of_instances(value, expected_type, field_name)  # Type validation for lists

# Field setters (for frozen dataclasses)
set_stripped_string(obj, field_name, value)    # Set string after stripping whitespace
set_normalized_string(obj, field_name, value, transform="none")  # Set with optional case transform
```

## Adding New Services

### 1. Adding a New Order Provider

**Goal:** Add support for a new order provider (e.g., "MyProvider").

#### Step 1: Implement IOrderService Interface

Create `src/services/myprovider_order_service.py`:

```python
from src.interfaces import IOrderService, IErrorQueue, IRegistry, IArtworkService
from src.domain import Order, OrderStatus

@dataclass(frozen=True, slots=True, kw_only=True)
class MyProviderOrderService:
    """Order service for MyProvider."""
    
    # Add any required configuration or clients
    api_url: str
    api_key: str
    input_dir: Path
    
    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create from global config."""
        return cls(
            api_url=config.myprovider_api_url,  # Add to config
            api_key=config.myprovider_api_key,
            input_dir=config.open_orders_dir,
        )
    
    # IOrderReader
    def read_orders(self) -> Generator[Order, None, None]:
        """Read orders from MyProvider API."""
        response = httpx.get(f"{self.api_url}/orders", headers={
            "Authorization": f"Bearer {self.api_key}"
        })
        for raw_order in response.json()["orders"]:
            yield self._parse_order(raw_order)
    
    def _parse_order(self, raw_order: dict) -> Order:
        """Convert raw API order to Order domain object."""
        return Order(
            administration_id=raw_order["admin_id"],
            customer_id=raw_order["customer_id"],
            order_provider="MyProvider",
            pricelist_id=raw_order.get("pricelist_id", 1),
            remote_order_id=raw_order["order_id"],
            shipment_type=raw_order.get("shipment_type", "standard"),
            description=raw_order.get("description", f"MyProvider Order {raw_order['order_id']}"),
            delivery_instructions=raw_order.get("delivery_instructions", ""),
            ship_to=ShipTo(
                remote_customer_id=raw_order["ship_to"]["customer_id"],
                company_name=raw_order["ship_to"]["company"],
                contact_name=raw_order["ship_to"]["contact"],
                email=raw_order["ship_to"]["email"],
                phone=raw_order["ship_to"]["phone"],
                street1=raw_order["ship_to"]["street"],
                city=raw_order["ship_to"]["city"],
                postal_code=raw_order["ship_to"]["zip"],
                country_code=raw_order["ship_to"]["country"],
            ),
            line_items=[
                LineItem(
                    line_id=line["line_no"],
                    product_code=line["sku"],
                    quantity=line["qty"],
                )
                for line in raw_order["lines"]
            ],
        )
    
    # IOrderStore
    def persist_order(self, order: Order, status: OrderStatus) -> None:
        """Save order status to MyProvider (or local cache)."""
        # Example: POST to MyProvider API
        # Or: Save to local JSON file
        order_file = self.input_dir / f"{order.remote_order_id}.json"
        order_file.write_text(json.dumps({
            "remote_order_id": order.remote_order_id,
            "status": status.value,
            "sale_id": order.sale_id,
        }))
    
    def load_order(self, remote_order_id: str) -> Order | None:
        """Load saved order from cache."""
        order_file = self.input_dir / f"{remote_order_id}.json"
        if not order_file.exists():
            return None
        # Reconstruct Order from cached data
        # (Implementation depends on what you cached)
    
    # IOrderNotifier
    def get_notify_data(self, order: Order, sale_service: ISaleService) -> dict:
        """Get data needed for notification (customer info, shipping, serials, etc.)."""
        # Gather information from sale_service and order
        return {
            "customer_name": sale_service.get_customer_name(order.sale_id),
            "shipping_address": sale_service.get_shipping_address(order.sale_id),
        }
    
    def notify_completed_sale(self, order: Order, notify_data: dict) -> None:
        """Notify MyProvider that sale is completed with EDIFACT message."""
        # Generate EDIFACT notification (D96A + D99A) and send/save
        # Example: httpx.post(f"{self.api_url}/orders/{order.remote_order_id}/notify",
        #                      json={"status": "completed", "sale_id": order.sale_id})
    
    # IArtworkServiceProvider
    def get_artwork_service(
        self, order: Order, artwork_services: IRegistry[IArtworkService]
    ) -> IArtworkService | None:
        """Select artwork service based on order."""
        # Logic to pick which artwork service to use
        # For MyProvider orders, use Spectrum
        return artwork_services.get("Spectrum")
```

#### Step 2: Register in main.py

```python
# src/main.py
from src.services.myprovider_order_service import MyProviderOrderService

def main() -> None:
    config = get_config()
    order_services = Registry[IOrderService]()
    
    # Register existing providers
    order_services.register("Harman", HarmanOrderService.from_config(config))
    
    # Register new provider
    order_services.register("MyProvider", MyProviderOrderService.from_config(config))
    
    # Rest of main() uses order_services.items() - works for all providers!
```

#### Step 3: Add Configuration

```python
# src/config.py - add to Config class
@dataclass(frozen=True, slots=True)
class Config:
    # ... existing config ...
    
    # MyProvider settings
    myprovider_api_url: str = os.getenv("MYPROVIDER_API_URL", "")
    myprovider_api_key: str = os.getenv("MYPROVIDER_API_KEY", "")
```

```bash
# .env
MYPROVIDER_API_URL=https://api.myprovider.com
MYPROVIDER_API_KEY=your_api_key
```

### 2. Adding a New Artwork Service

**Goal:** Add a new artwork provider (e.g., "LocalFilesystem").

Create `src/services/local_filesystem_artwork_service.py`:

```python
from src.interfaces import IArtworkService
from src.domain import Order

@dataclass(frozen=True, slots=True, kw_only=True)
class LocalFilesystemArtworkService:
    """Get artwork from local filesystem."""
    
    artwork_dir: Path
    
    def get_artwork(self, order: Order) -> list[Path]:
        """Fetch artwork files from local filesystem."""
        artwork_files = []
        for line_item in order.line_items:
            product_dir = self.artwork_dir / line_item.product_code
            if product_dir.exists():
                artwork_files.extend(product_dir.glob("*.pdf"))
        return artwork_files
```

Register in `main.py`:

```python
artwork_services.register("LocalFS", LocalFilesystemArtworkService(
    artwork_dir=config.digitals_dir
))
```

### 3. Adding a New Stock Service

**Goal:** Add a new stock/inventory provider.

Create `src/services/myprovider_stock_service.py`:

```python
from src.interfaces import IStockService
from pathlib import Path
from typing import Any, Generator

@dataclass(frozen=True, slots=True, kw_only=True)
class MyProviderStockService:
    """Handle stock transfers with MyProvider."""
    
    api_url: str
    api_key: str
    output_dir: Path
    
    def read_stock_transfers(self) -> Generator[dict[str, Any], None, None]:
        """Read pending stock transfer requests."""
        response = httpx.get(f"{self.api_url}/stock_transfers",
                           headers={"Authorization": f"Bearer {self.api_key}"})
        for transfer in response.json()["transfers"]:
            yield transfer
    
    def create_stock_transfer_reply(self, transfer_data: dict[str, Any]) -> Path:
        """Create a reply file for the stock transfer.
        
        Args:
            transfer_data: Stock transfer request data
            
        Returns:
            Path to the created reply file
        """
        # Create reply content (format depends on provider)
        reply_content = self._build_reply(transfer_data)
        
        # Write to output directory
        reply_path = self.output_dir / f"reply_{transfer_data['id']}.xml"
        reply_path.write_text(reply_content)
        
        return reply_path
    
    def email_stock_transfer_reply(self, reply_path: Path, transfer_data: dict[str, Any]) -> None:
        """Email the stock transfer reply file.
        
        Args:
            reply_path: Path to the reply file to send
            transfer_data: Original transfer request data (for context)
        """
        # Configure email client and send
        emailer = EmailSender(host=config.smtp_host, port=config.smtp_port)
        emailer.send(
            subject=f"Stock Transfer Reply {transfer_data['id']}",
            sender=config.email_sender,
            receivers=config.email_stock_to,
            attachments={reply_path.name: reply_path.read_bytes()},
        )
    
    def mark_transfer_as_processed(self, transfer_data: dict[str, Any]) -> None:
        """Mark the stock transfer as processed.
        
        Args:
            transfer_data: Stock transfer request data
        """
        # Rename input file or update status in provider system
        input_path = Path(transfer_data["file_path"])
        if input_path.exists():
            processed_path = input_path.parent / f"{input_path.name}.processed"
            input_path.rename(processed_path)
    
    def _build_reply(self, transfer_data: dict[str, Any]) -> str:
        """Build reply content for the transfer."""
        # Format reply according to provider specification
        pass
```

Register in `main.py`:

```python
stock_services.register("MyProvider", MyProviderStockService.from_config(config))
```

**Key Points:**
- `read_stock_transfers()` yields transfer request dictionaries
- `create_stock_transfer_reply()` creates a reply file and returns its Path
- `email_stock_transfer_reply()` sends the reply file to configured recipients
- `mark_transfer_as_processed()` marks the transfer as processed (e.g., renames input file)
- If any step fails, the transfer remains unprocessed (no file rename)
- Use StockTransferUseCase to orchestrate all three steps

### 4. Understanding SpectrumArtworkService (Reference Implementation)

The `SpectrumArtworkService` is a complete, production-ready artwork service example. Key patterns to follow:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class SpectrumArtworkService:
    """Retrieve and manage digital artwork from Spectrum API."""
    
    session: requests.Session                  # HTTP client
    api_key: InitVar[str]                      # API authentication key
    api_key: InitVar[str]                      # API authentication key
    base_url: str                              # API base URL
    digitals_dir: Path                         # Local storage
    client_handle: str = field(init=False)     # Set in __post_init__
    order_data: dict = field(init=False)       # Cached from API
    
    def __post_init__(self, api_key: str) -> None:
    def __post_init__(self, api_key: str) -> None:
        """Initialize authorization headers and API session."""
        # Configure session headers with authentication token
        self.session.headers.update({"SPECTRUM_API_TOKEN": api_key})
        # Configure session headers with authentication token
        self.session.headers.update({"SPECTRUM_API_TOKEN": api_key})
        # Extract client_handle from order response
        # Store order data for subsequent requests
        # Store order data for subsequent requests
        object.__setattr__(self, "client_handle", extracted_value)
        object.__setattr__(self, "order_data", response_data)
    
    def get_artwork(self, order: Order) -> list[Artwork]:
        """Retrieve artwork for order, extract files, validate results.
        
        Args:
            order: Order to fetch artwork for
            
        Returns:
            List of Artwork objects with validated file paths
            
        Raises:
            ArtworkError: When API calls fail or validation fails
        """
        # Orchestrate: fetch data → get designs → get placements → validate
        # Ensure all files exist locally before returning Artwork objects
        # On any error, raise ArtworkError with order context
        pass
    
    def _get_order_data(self) -> dict:
        """Fetch order metadata from API."""
        # Single responsibility: HTTP call + response handling
        pass
    
    def _download_designs(self) -> list[str]:
        """List available designs for order."""
        pass
    
    def _download_placement(self, design_id: str) -> Path:
        """Download and extract placement files."""
        # Extract to digitals_dir
        # Return local Path object
        pass
```

**Key Patterns:**
1. **Frozen Dataclass** - Immutable after `__post_init__`
2. **init=False Fields** - Avoid constructor params, set in `__post_init__` using `object.__setattr__`
3. **Single Task Methods** - Each private method does one thing (_get_order_data, _download_designs, _download_placement)
4. **Validation in Public Method** - get_artwork orchestrates and validates, never returns invalid results
5. **Comprehensive Docstrings** - Args, Returns, Raises for public methods
6. **Error Handling** - Raise custom ArtworkError with context, catch in ErrorStore

## Testing

### Test Coverage

Comprehensive test suite with **862 unit tests** and high code coverage:

**Module Coverage Levels:**
- **Domain Layer** (100% coverage) - Order, ShipTo, LineItem, Artwork, Validators - comprehensive validation and state transition testing
- **Application Layer** (100% coverage) - All use cases (NewSalesUseCase, CompletedSaleUseCase, StockTransferUseCase) with mocked services
- **Services Layer** (78-100% coverage):
  - HarmanOrderService: 52 tests (78% coverage) - Order parsing, EDIFACT processing
  - OdooSaleService: 66 tests (95% coverage) - Sale management, JSON-RPC integration
  - SpectrumArtworkService: 35+ tests (100% coverage) - Design retrieval, file handling
  - RenderService: 100% coverage - Template rendering
  - HarmanStockService: 100% coverage - Stock transfers
  
**Overall:** 87% code coverage across all modules

**Test Files (24 total):**
- Unit tests: `tests/unit/` (19 test files)
  - Domain tests: Order, ShipTo, LineItem, Artwork, Validators
  - Service tests: Harman, Odoo, Spectrum, Render (with mocked HTTP)
  - Use case tests: NewSale, CompletedSale, StockTransfer (with mocked services)
  - Config tests: Configuration loading and validation
- Integration tests: `tests/integration/` (5 test files)
  - Cross-module testing validating service interactions
  - Main setup and workflow integration tests

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run with coverage report
uv run pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/domain/test_order.py -v

# Run specific test class
uv run pytest tests/unit/services/test_odoo_sale_service.py::TestMarkSaleNotified -v

# Run integration tests
uv run pytest tests/integration/ -v
```

### Writing Tests for New Services

Example: Testing `MyProviderOrderService`

```python
# tests/unit/services/test_myprovider_order_service.py
import pytest
from unittest.mock import Mock
import httpx
from pytest_httpx import HTTPXMock

from src.services.myprovider_order_service import MyProviderOrderService

class TestMyProviderOrderService:
    
    @pytest.fixture
    def service(self):
        return MyProviderOrderService(
            api_url="https://api.test.com",
            api_key="test_key",
            input_dir=Path("/tmp"),
        )
    
    def test_read_orders_success(self, service, httpx_mock: HTTPXMock):
        """Test reading orders from API."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.test.com/orders",
            json={
                "orders": [
                    {
                        "order_id": "ORD001",
                        "admin_id": 1,
                        "customer_id": 100,
                        # ... more fields
                    }
                ]
            }
        )
        
        orders = list(service.read_orders())
        
        assert len(orders) == 1
        assert orders[0].remote_order_id == "ORD001"
```

## Error Handling

### Error Store Pattern

Instead of exceptions propagating up the stack and stopping execution, they're collected centrally in ErrorStore:

```python
# In main.py
error_store = get_error_store()

# Execute each use case, collecting errors
for _, use_case in use_cases.items():
    try:
        use_case.execute()
    except Exception as exc:
        error_store.add(exc)
        logger.error(f"Error executing use case: {exc!s}")

# At the end, check if errors occurred and send alert email
if error_store.has_errors():
    emailer = EmailSender(...)
    emailer.send(
        subject="Deonet External Order - Errors during execution",
        body_params=error_store.get_render_email_data(),
    )
```

This ensures that:
- One failing service doesn't stop other services from executing
- All errors are collected and reported together
- The IT team receives an email alert with complete error details
- Execution continues even if individual orders fail

### Custom Error Types

```python
# src/app/errors.py

class SaleError(Exception):
    """Error during sale creation/processing."""
    def __init__(self, message: str, order_id: str):
        self.order_id = order_id
        super().__init__(message)

class NotifyError(Exception):
    """Error during order notification."""
    def __init__(self, message: str, order_id: str):
        self.order_id = order_id
        super().__init__(message)

class ArtworkError(Exception):
    """Error during artwork retrieval."""
    pass
```

Throw errors for critical failures:

```python
# In order service
if not order_data:
    raise NotifyError("No valid order data found", order_id=order.remote_order_id)
```

## Development Workflow

### Code Style & Conventions

- **Type hints** are required on all functions and classes
- **Comprehensive docstrings** required:
  - Module docstrings: Concise one/two-line purpose description
  - Class docstrings: Clear purpose with Attributes section for dataclasses
  - Method/function docstrings: Args, Returns, Raises sections for complex methods, one-liners for simple ones
  - All core modules standardized with consistent style (see spectrum_artwork_service.py as reference)
  - Action-oriented language preferred ("Retrieve", "Parse", "Create", "Validate")
- **Frozen dataclasses** used for immutable domain objects with validation in `__post_init__()`
- **Protocols** instead of abstract base classes for interfaces (contract-based design)
- **Single responsibility** - each class has one reason to change
- **Error handling**: Exceptions collected in ErrorStore, not propagated (fail-safe pattern)
- **init=False fields**: Use for state that's derived/set in `__post_init__()` (requires `object.__setattr__()` due to frozen dataclass)
- **Conditional workflow steps**: Use walrus operator in conditionals when assigning and testing simultaneously (e.g., `if (artwork := get_artwork()) is not None:`)

### Project Structure Decisions

1. **`src/` directory structure mirrors DDD layers:**
   - Domain → no external dependencies
   - Services → external integrations
   - App → orchestration/coordination
   - Interfaces → contracts

2. **Services are stateless:**
   - No internal state mutation
   - Accept parameters, return results
   - Thread-safe by default

3. **Validation at the boundary:**
   - Domain objects validate on creation
   - Services validate inputs before processing
   - Use case layer catches and logs exceptions

### Adding a New Module

If you need to add a new cross-cutting concern (e.g., logging, caching):

```python
# src/utils/cache.py (new utility module)
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_expensive_operation(key: str) -> Result:
    """Cache results of expensive operation."""
    pass

# Then import and use in services
from src.utils.cache import cached_expensive_operation
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-service

# Make changes, test, commit
uv run pytest tests/ -v  # Verify all tests pass
git add .
git commit -m "Add new artwork service"

# Push and create PR
git push origin feature/new-service

# Before merging:
# 1. Verify all tests pass with: uv run pytest -q
# 2. Ensure new code has type hints and comprehensive docstrings
# 3. Check that error handling collects to ErrorStore singleton (not print/raise)
```

## Dependencies

### Production Dependencies

| Package         | Purpose                                          |
| --------------- | ------------------------------------------------ |
| `requests`      | HTTP client for API calls with timeout support   |
| `jinja2`        | Template engine for EDIFACT rendering            |
| `pydifact`      | EDIFACT EDI message parsing/generation           |
| `python-dotenv` | Environment variable loading from `.env` files   |
| `redmail`       | SMTP email client for error alerts and notifications |
| `xmltodict`     | XML to dictionary conversion (Harman stock API)  |

### Development Dependencies

| Package        | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `pytest`       | Test runner & assertion framework (894 tests)       |
| `pytest-cov`   | Code coverage measurement (94% coverage)             |
| `pytest-mock`  | Mocking and patching utilities                       |
| `types-requests` | Type hints for requests library                    |

### Why These Choices

**Production Packages:**
- **requests** - Widely used HTTP client with clear API, excellent error handling, robust connection management
- **Jinja2** - Industry standard for templating, excellent EDIFACT format support, powerful expression language
- **pydifact** - Purpose-built EDIFACT parser vs rolling our own, handles D96A/D99A EDI standards correctly
- **python-dotenv** - Simple, convention-based config management, works well with 12-factor app principles
- **redmail** - High-level SMTP wrapper that simplifies email sending with template support
- **xmltodict** - Lightweight XML-to-dict conversion for Harman stock API responses

**Development Packages:**
- **pytest** - Superior fixture system, better assertions, excellent plugin ecosystem (pytest-mock, pytest-cov)
- **pytest-cov** - Integrated coverage reporting with HTML output via `--cov-report=html`
- **pytest-mock** - Cleaner mocking API than unittest.mock, better pytest integration
- **types-requests** - Type hints for requests library, enables better IDE support and type checking

## Project Status

### Latest Release Highlights

✅ **Comprehensive Test Suite with High Coverage**
- **Unit Tests**: 80+ tests covering all critical components
  - `spectrum_artwork_service.py` - 35 tests with 100% coverage
  - `new_sale_use_case.py` - 40 tests with 100% coverage
  - Domain models and validators - Full coverage
- **Integration Tests**: 4+ integration tests for cross-module workflows
- **Test Framework**: pytest with mock support (pytest-mock), httpx mocking (pytest-httpx)
- Run with: `uv run pytest tests/ -q` or `uv run pytest tests/ -v`

✅ **Comprehensive Docstrings with Full Documentation**
- **All core modules** - Complete docstrings with Args/Returns/Raises sections
- **Service methods** - Detailed documentation of parameters and behavior
- **Domain models** - Clear purpose with Attributes documentation
- **Interfaces** - 13+ Protocol definitions with method contracts
- **Complete implementation** - 5 service implementations:
  - HarmanOrderService - EDIFACT order EDI processing
  - HarmanStockService - Stock transfer handling
  - OdooSaleService - JSON-RPC CRM integration
  - RenderService - Jinja2 template rendering
  - SpectrumArtworkService - Artwork retrieval and management (35 tests)

✅ **Simplified Error Handling**
- Centralized ErrorStore pattern for collecting exceptions
- Email alerts sent to IT team with complete error details
- Fail-safe design ensures partial failures don't block other services
- All use cases continue executing even if individual orders fail

### Architecture Quality

- **Clean Architecture** - Strict separation of concerns (Domain, App, Services, Interfaces)
- **Plugin Architecture** - Service registries allow runtime registration of new providers
- **Protocol-Based Interfaces** - Contract-driven design using Python Protocols
- **Immutable Domain Objects** - Frozen dataclasses with validation in `__post_init__()`
- **Type-Safe** - Full type hints on all functions and classes
- **Well-Tested** - 894 tests with 94% coverage providing strong regression protection

### Ready for Production

This codebase is production-ready with:
- Complete test coverage of core workflows
- Comprehensive documentation for all modules and classes
- Robust error handling and alerting
- Clean, maintainable architecture supporting extension and modification

### Adding New Dependencies

```bash
# Add production dependency
uv add new-package

# Add dev-only dependency
uv add --group dev new-dev-package

# Update lock file
uv sync
```

---

## Quick Reference

### Common Commands

```bash
# Setup
uv sync                                    # Install all dependencies

# Development
uv run pytest tests/ -v                    # Run all 894 tests
uv run pytest tests/ --cov=src             # With coverage report
uv run pytest tests/ --cov-report=html     # HTML coverage report
uv run python -m src.main                  # Run application

# Configuration
export ODOO_BASE_URL="https://..."
export SPECTRUM_HARMAN_API_KEY="..."
uv run python -m src.main

# Code quality
uv run pytest tests/ -q                    # Quiet output (all tests passing)
uv run pytest tests/ --lf                  # Last failed tests only
uv run pytest tests/ -k test_name          # Run specific test
uv run pytest tests/unit/services/test_spectrum_artwork_service.py -v  # Specific file

```

### Key Files to Understand

1. **`src/main.py`** - Start here to understand the overall flow
2. **`src/interfaces/base.py`** - Understand the service contracts
3. **`src/app/new_sale_use_case.py`** - See how use cases orchestrate services
4. **`src/services/harman_order_service.py`** - Example of a complete service implementation
5. **`src/config.py`** - Configuration management

---

**Questions? Issues? Submit them to the project's issue tracker.**
