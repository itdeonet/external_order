# Deonet External Order - Codebase Structure & API Reference

## Overview
This is a Python application for processing external orders from multiple order providers (Harman, Spectrum) and integrating them with an Odoo sales system. It follows hexagonal architecture principles with clear separation of domain models, service implementations, and use case orchestration.

---

## 1. Directory Structure

```
src/
├── main.py                          # Application entry point & dependency injection
├── config.py                         # Configuration management (frozen dataclass)
├── order-json-converter.py          # Standalone conversion utility
│
├── domain/                          # Domain models & ports (interfaces)
│   ├── __init__.py                  # Exports domain models and interfaces
│   ├── order.py                     # Order aggregate root with OrderStatus enum
│   ├── line_item.py                 # LineItem model (product + artwork)
│   ├── ship_to.py                   # ShipTo address model
│   ├── artwork.py                   # Artwork model (design + placement files)
│   ├── validators.py                # Validation & normalization utilities
│   └── ports.py                     # Protocol interfaces (IOrderService, ISaleService, etc.)
│
├── app/                             # Application layer (use cases & wiring)
│   ├── new_sale_use_case.py        # Create new sales from orders
│   ├── completed_sale_use_case.py  # Handle completed sales notifications
│   ├── stock_transfer_use_case.py  # Process stock transfer requests
│   ├── registry.py                 # Thread-safe registry for service instances
│   ├── odoo_auth.py                # Odoo RPC credentials (frozen dataclass)
│   ├── errors.py                   # ErrorStore & custom exception classes
│   └── log_setup.py                # Logging configuration
│
├── services/                        # Service implementations (external integrations)
│   ├── harman_order_service.py     # EDIFACT order parsing & Harman integration
│   ├── harman_stock_service.py     # Stock transfer XML processing
│   ├── odoo_sale_service.py        # Odoo sales RPC operations
│   ├── spectrum_artwork_service.py # Spectrum API artwork retrieval
│   └── render_service.py           # Jinja2 template rendering
│
└── templates/                       # EDI & email templates
    ├── desadvd96a.j2               # DESADV D96A format template
    ├── desadvd99a.j2               # DESADV D99A format template
    ├── error_alert.html            # Error notification email template
    └── stock_email.html            # Stock transfer confirmation template
```

---

## 2. Interfaces/Protocols (Domain Ports)

All interfaces are defined in [src/domain/ports.py](src/domain/ports.py) as Protocol classes.

### `IUseCase`
Represents executable workflow.
```python
class IUseCase(Protocol):
    def execute(self) -> None:
        """Run the use case workflow."""
```

### `IRegistry[T]`
Thread-safe generic registry for named service instances.
```python
class IRegistry[T](Protocol):
    def register(self, name: str, obj: T) -> None
    def get(self, name: str) -> T | None
    def unregister(self, name: str) -> None
    def clear(self) -> None
    def items(self) -> Generator[tuple[str, T], None, None]
```

### `IArtworkService`
Retrieves artwork files for an order.
```python
class IArtworkService(Protocol):
    def get_artwork(self, order: "Order") -> list[Path]:
        """Return local file list of artwork files for order."""
```

### `IOrderReader`
Reads orders from a provider.
```python
class IOrderReader(Protocol):
    def read_orders(self) -> Generator["Order", None, None]:
        """Yield Order instances from provider."""
```

### `IOrderStore`
Persists and loads orders.
```python
class IOrderStore(Protocol):
    def persist_order(self, order: "Order", status: "OrderStatus") -> None
    def load_order(self, remote_order_id: str) -> "Order"
```

### `IOrderNotifier`
Notifies providers of completed sales.
```python
class IOrderNotifier(Protocol):
    def get_notify_data(self, order: "Order", sale_service: "ISaleService") -> dict[str, Any]
    def notify_completed_sale(self, order: "Order", notify_data: dict[str, Any]) -> None
```

### `IArtworkServiceProvider`
Selects artwork service for an order.
```python
class IArtworkServiceProvider(Protocol):
    def get_artwork_service(
        self, order: "Order", artwork_services: "IRegistry[IArtworkService]"
    ) -> IArtworkService | None
```

### `IOrderService`
Composite protocol aggregating order operations.
```python
class IOrderService(IOrderReader, IOrderStore, IOrderNotifier, IArtworkServiceProvider, Protocol):
    def should_update_sale(self, order: "Order") -> bool
        """Determine if existing sale should be updated."""
```

### `ISaleService`
Creates, manages, and queries sales.
```python
class ISaleService(Protocol):
    def create_sale(self, order: "Order") -> tuple[int, str]  # Returns (sale_id, sale_name)
    def sale_has_expected_order_lines(self, order: "Order") -> bool
    def update_contact(self, order: "Order") -> None
    def update_sale(self, order: "Order") -> None
    def search_sale(self, order: "Order") -> dict[str, Any]
    def search_completed_sales(self, order_provider: str) -> list[tuple[int, str]]
    def mark_sale_notified(self, sale_id: int) -> None
    def search_shipping_info(self, order: "Order") -> list[dict[str, Any]]
    def search_serials_by_line_item(self, order: "Order") -> dict[str, list[str]]
```

### `IStockService`
Reads and processes stock transfer notifications.
```python
class IStockService(Protocol):
    def read_stock_transfers(self) -> Generator[dict[str, Any], None, None]
    def create_stock_transfer_reply(self, transfer_data: dict[str, Any]) -> Path
    def email_stock_transfer_reply(self, reply_path: Path, transfer_data: dict[str, Any]) -> None
    def mark_transfer_as_processed(self, transfer_data: dict[str, Any]) -> None
```

---

## 3. Domain Models

### `Order` (Aggregate Root)
Located in [src/domain/order.py](src/domain/order.py)

**Fields (frozen, immutable):**
- `administration_id: int` - Odoo company ID
- `customer_id: int` - Odoo customer ID
- `order_provider: str` - Provider name (e.g., "HARMAN JBL")
- `pricelist_id: int` - Odoo pricelist ID
- `remote_order_id: str` - External provider's order ID
- `shipment_type: str` - Shipping method
- `description: str` - Order description
- `delivery_instructions: str` - Special instructions (default: "")
- `ship_to: ShipTo` - Shipping address
- `line_items: list[LineItem]` - Product lines
- `sale_id: int` - Odoo sale ID (default=0, set via method)
- `sale_name: str` - Odoo sale order name (default="", set via method)
- `status: OrderStatus` - Current state (NEW, CREATED, ARTWORK, CONFIRMED, COMPLETED, SHIPPED, FAILED)
- `created_at: str` - ISO datetime string
- `ship_at: str` - ISO date string

**Methods:**
- `__post_init__()` - Validates all fields on construction
- `set_sale_id(value: int) -> None` - Set the sale ID (requires positive integer)
- `set_sale_name(value: str) -> None` - Set the sale name (requires non-empty string)
- `set_status(value: OrderStatus) -> None` - Set order status
- `set_created_at(created_at: dt.datetime) -> None` - Set creation timestamp
- `set_ship_at(ship_at: dt.date) -> None` - Set shipping date
- `calculate_delivery_date(workdays: int) -> dt.date` - Static method to calculate delivery date

**Enum: `OrderStatus`**
```python
class OrderStatus(Enum):
    NEW = "new"
    CREATED = "created"
    ARTWORK = "artwork"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    SHIPPED = "shipped"
    FAILED = "failed"
```

### `ShipTo` (Value Object)
Located in [src/domain/ship_to.py](src/domain/ship_to.py)

**Fields (frozen, immutable):**
- `remote_customer_id: str` - External customer ID
- `company_name: str` - Company name (optional, default="")
- `contact_name: str` - Contact person name
- `email: str` - Email address (normalized to lowercase)
- `phone: str` - Phone number
- `street1: str` - Primary street address
- `street2: str` - Secondary street address (optional, default="")
- `city: str` - City
- `state: str` - State/province (optional, default="")
- `postal_code: str` - Postal code (normalized to uppercase)
- `country_code: str` - 2-letter ISO country code (normalized to uppercase)

**Validation:**
- All non-optional fields are validated as non-empty strings
- Email must be valid email format (normalized lowercase)
- Phone contains only digits and valid chars: `+-() `
- Country code must be exactly 2 letters

### `LineItem` (Value Object)
Located in [src/domain/line_item.py](src/domain/line_item.py)

**Fields (frozen, immutable):**
- `line_id: str` - Line item identifier
- `product_code: str` - Product SKU/code
- `quantity: int` - Order quantity (positive integer)
- `artwork: Artwork | None` - Optional artwork files (default=None)

**Methods:**
- `__post_init__()` - Validates fields
- `set_artwork(artwork: Artwork) -> None` - Set artwork for this line

### `Artwork` (Value Object)
Located in [src/domain/artwork.py](src/domain/artwork.py)

**Fields (frozen, immutable):**
- `artwork_id: str` - Artwork/recipe set identifier
- `artwork_line_id: str` - Line item this artwork belongs to
- `design_url: str` - URL to design specification
- `design_paths: list[Path]` - Local file paths to design files (must exist)
- `placement_url: str` - URL to placement specification
- `placement_path: Path` - Local file path to placement PDF (must exist)

**Validation:**
- All string fields must be non-empty
- Design/placement paths must exist as files
- Design paths must be non-empty list

### Validators
Located in [src/domain/validators.py](src/domain/validators.py)

**Public validation functions:**
- `validate_positive_int(value, field_name)` - Raises if not positive integer
- `validate_non_negative_int(value, field_name)` - Raises if negative or not integer
- `validate_non_empty_string(value, field_name) -> str` - Returns stripped string
- `validate_optional_string(value, field_name) -> str` - Returns stripped or empty
- `validate_instance[T](value, expected_type, field_name)` - Type check
- `validate_list_of_instances[T](value, expected_type, field_name, allow_empty)` - List type check
- `validate_email(value, field_name="Email") -> str` - Returns normalized lowercase email
- `validate_phone(value, field_name="Phone") -> str` - Returns stripped phone
- `validate_country_code(value, field_name="Country code") -> str` - Returns uppercase 2-letter code
- `set_normalized_string(obj, field_name, value, transform="none")` - Set with optional case transform

---

## 4. Service Implementations

### `HarmanOrderService`
Located in [src/services/harman_order_service.py](src/services/harman_order_service.py)

Implements: `IOrderService` (read, store, notify, artwork selection)

**Configuration fields (from Config):**
- `administration_id: int` - Odoo company ID (default from config)
- `customer_id: int` - Odoo customer ID (default from config)
- `pricelist_id: int` - Pricelist ID (default from config)
- `order_provider: str` - "HARMAN JBL" (default from config)
- `shipment_type: str` - "harman%" (default from config)
- `workdays_for_delivery: int` - Default delivery days (default from config)
- `input_dir: Path` - Directory for input EDIFACT files (harman/in)
- `output_dir: Path` - Directory for output files (harman/out)
- `renderer: RenderService` - Template renderer for DESADV messages

**Public methods:**
- `read_orders() -> Generator[Order, None, None]` - Parse .insdes/.new/.created/.artwork files
- `get_artwork_service(order, artwork_services) -> IArtworkService | None` - Return Spectrum service for matching orders or None
- `should_update_sale(order) -> bool` - True if order ID matches format S\d+ (created in Odoo)
- `persist_order(order, status) -> None` - Save order as JSON and rename EDIFACT file
- `load_order(remote_order_id) -> Order` - Load previously persisted JSON order
- `notify_completed_sale(order, notify_data) -> None` - Generate DESADV D96A/D99A messages
- `get_notify_data(order, sale_service) -> dict[str, Any]` - Prepare data for DESADV templates

**Private methods:**
- `_read_order_data(file) -> dict[str, Any]` - Parse EDIFACT file
- `_get_segment_data(segment, order_data) -> dict[str, Any]` - Extract segment data
- `_make_order(data) -> Order` - Create Order from parsed data
- `read_order_data_by_remote_order_id(remote_order_id) -> dict[str, Any] | None` - Find archived file

### `HarmanStockService`
Located in [src/services/harman_stock_service.py](src/services/harman_stock_service.py)

Implements: `IStockService`

**Configuration fields:**
- `input_dir: Path` - XML file input directory (harman/in)
- `output_dir: Path` - Reply output directory (harman/out)

**Public methods:**
- `read_stock_transfers() -> Generator[dict[str, Any], None, None]` - Parse XML files and yield transfer data
- `create_stock_transfer_reply(transfer_data) -> Path` - Create IN05 reply XML file and return its path
- `email_stock_transfer_reply(reply_path, transfer_data) -> None` - Send reply file as email attachment
- `mark_transfer_as_processed(transfer_data) -> None` - Rename input file to mark as processed

**Private methods:**
- `_get_transfer_info(transfer_data, file_path) -> dict[str, Any]` - Extract transfer metadata

**Transfer data structure:**
```python
{
    "file_path": str,         # Source XML path
    "idoc_number": str,       # IDOC message number
    "idoc_datetime": datetime,# Message creation time
    "delivery_number": str,   # Delivery ID
    "items": [                # Stock items
        {
            "item_number": str,
            "product_code": str,
            "quantity": int,
            "storage_location": str
        }
    ]
}
```

### `OdooSaleService`
Located in [src/services/odoo_sale_service.py](src/services/odoo_sale_service.py)

Implements: `ISaleService`

**Configuration fields:**
- `session: requests.Session` - HTTP session (required, passed in)
- `auth: OdooAuth` - RPC credentials (frozen dataclass with database, user_id, password)
- `base_url: str` - Odoo JSON-RPC endpoint URL

**Public methods:**
- `create_sale(order) -> tuple[int, str]` - Create new Odoo sale and return (sale_id, sale_name)
- `sale_has_expected_order_lines(order) -> bool` - Check line count matches
- `update_contact(order) -> None` - Update shipping contact details
- `update_sale(order) -> None` - Update sale from order data
- `search_sale(order) -> dict[str, Any]` - Find sale by remote_order_id
- `search_completed_sales(order_provider) -> list[tuple[int, str]]` - Find completed sales
- `mark_sale_notified(sale_id) -> None` - Set notification flag
- `search_shipping_info(order) -> list[dict[str, Any]]` - Get tracking/shipment data
- `search_serials_by_line_item(order) -> dict[str, list[str]]` - Map serials to line items

**Private methods:**
- `__post_init__()` - Validate auth, session, base_url
- `_search_country_id(country_code) -> int` - Look up country record
- `_search_state_id(country_id, state) -> int` - Look up state record
- `_load_contact_data_from_order(order) -> dict[str, Any]` - Convert ShipTo to contact fields
- `_create_contact(order) -> int` - Create or find contact
- `_convert_order_lines(order) -> list[dict[str, Any]]` - Map LineItems to Odoo products
- `_search_carrier_id(order) -> int` - Find shipping carrier
- `_call(model, method, query_data, query_options) -> Any` - Authenticated JSON-RPC

### `SpectrumArtworkService`
Located in [src/services/spectrum_artwork_service.py](src/services/spectrum_artwork_service.py)

Implements: `IArtworkService`

**Configuration fields:**
- `session: requests.Session` - HTTP session with API token header (required, passed in)
- `base_url: str` - Spectrum API base URL (from config)
- `digitals_dir: Path` - Directory where artwork files are saved (from config)
- `client_handle: str` - Spectrum client handle (cached from API response)
- `order_data: dict[str, Any]` - Cached Spectrum order data

**Public methods:**
- `get_artwork(order) -> list[Path]` - Query Spectrum API, download designs + placement, update line items
- `__post_init__()` - Set API token header

**Private methods:**
- `_load_order_data(order) -> None` - Fetch order from Spectrum API
- `_download_designs(recipe_set_id, sale_name) -> list[Path]` - Extract ZIP to digitals_dir with sale_name prefix
- `_download_placement(recipe_set_id, sale_name) -> Path` - Save placement PDF with sale_name prefix

**File naming:** `{sale_name}_{filename}` (e.g., "SO-12345_design.pdf", "SO-12345_RECIPE001_placement.pdf") (e.g., "SO-12345_design.pdf")

### `RenderService`
Located in [src/services/render_service.py](src/services/render_service.py)

Template rendering using Jinja2.

**Configuration fields:**
- `directory: Path` - Template directory (from config: src/templates)
- `env: Environment` - Jinja2 environment (created in __post_init__)

**Public methods:**
- `render(template_name, data) -> str` - Render template with data

---

## 5. Application Layer

### Use Cases

#### `NewSaleUseCase`
Located in [src/app/new_sale_use_case.py](src/app/new_sale_use_case.py)

**Process:**
1. Read orders from all registered order services
2. For each order:
   - Persist with status NEW
   - Search for existing sale OR create new sale
   - Check if sale needs update
   - Retrieve artwork (if applicable)
   - Confirm sale in Odoo
   - Persist with final status

**Dependencies:**
- `order_services: IRegistry[IOrderService]`
- `artwork_services: IRegistry[IArtworkService]`
- `sale_service: ISaleService`
- `open_orders_dir: Path`

**Methods:**
- `execute() -> None` - Run the workflow
- `organize_placement_files(order, artwork_files) -> list[Path]` - Copy placement files to order directory

#### `CompletedSaleUseCase`
Located in [src/app/completed_sale_use_case.py](src/app/completed_sale_use_case.py)

**Process:**
1. Search for completed sales for each order provider
2. For each completed sale:
   - Load order from persisted state
   - Get notification data from order service
   - Notify provider of completion
   - Mark sale as notified
   - Persist order with COMPLETED status

**Dependencies:**
- `order_services: IRegistry[IOrderService]`
- `sale_service: ISaleService`

**Methods:**
- `execute() -> None` - Run the workflow

#### `StockTransferUseCase`
Located in [src/app/stock_transfer_use_case.py](src/app/stock_transfer_use_case.py)

**Process:**
1. Read stock transfers from all registered stock services
2. For each transfer:
   - Generate reply
   - Send confirmation email
   - Rename input file to .replied

**Dependencies:**
- `stock_services: IRegistry[IStockService]`

**Methods:**
- `execute() -> None` - Run the workflow

### Registry
Located in [src/app/registry.py](src/app/registry.py)

**Implementation of `IRegistry[T]`**

**Features:**
- Thread-safe (uses Lock)
- Frozen dataclass with internal dict
- Methods: register, get, unregister, clear, items (generator)

### Error Handling
Located in [src/app/errors.py](src/app/errors.py)

**`ErrorStore` class:**
- Thread-safe collector for exceptions
- `add(exc: Exception) -> None` - Store with traceback
- `has_errors() -> bool` - Check if any errors stored
- `all() -> list[str]` - Get formatted tracebacks
- `summarize() -> str` - Single multi-line string
- `get_render_email_data() -> dict` - For email template rendering
- `clear() -> None` - Remove all errors
- `get_error_store() -> ErrorStore` - Cached singleton

**Custom Exceptions:**
- `BaseError(message, order_id=None)` - Base with optional order context
- `ArtworkError` - Artwork retrieval failures
- `InsdesError` - EDIFACT processing errors
- `NotifyError` - Provider notification failures
- `SaleError` - Odoo sale operation failures

### Authentication
Located in [src/app/odoo_auth.py](src/app/odoo_auth.py)

**`OdooAuth` class:**
```python
@dataclass(frozen=True, slots=True, kw_only=True)
class OdooAuth:
    database: str           # From ODOO_DATABASE env var
    user_id: int           # From ODOO_RPC_USER_ID env var
    password: str          # From ODOO_RPC_PASSWORD env var
```
- Validated in `__post_init__()` - raises ValueError if invalid
- Database, user_id, password must be non-empty
- User ID must be positive integer

### Logging
Located in [src/app/log_setup.py](src/app/log_setup.py)

**Configuration:**
- Console handler: WARNING level
- File handler: DEBUG level (configurable)
- Format: `%(asctime)s | %(name)s | %(levelname)s | %(message)s`
- Rotating file handler: daily rotation, 14 backups default
- Special handling: httpx, httpcore suppressed to INFO

---

## 6. Configuration

Located in [src/config.py](src/config.py)

**`Config` class (frozen dataclass):**

**Application Settings:**
- `default_box_size: tuple[int, int, int]` - Box dimensions in cm (L, W, H) = (24, 21, 6)
- `digitals_dir: Path` - Artwork downloads (derived: work_dir/digitals)
- `open_orders_dir: Path` - Placement files (derived: work_dir/open_orders)
- `sale_company_name: str` - "Deonet Production B.V."
- `ssl_verify: bool` - SSL verification flag (env: SSL_VERIFY, default: true)
- `templates_dir: Path` - Template location (src/templates)
- `work_dir: Path` - Base data directory (env: WORK_DIR, default: ~/projects-data/external_order)

**Email Settings:**
- `smtp_host: str` - SMTP relay (env: SMTP_HOST, default: "smtp-relay.gmail.com")
- `smtp_port: int` - SMTP port (env: SMTP_PORT, default: 587)
- `email_sender: str` - From address (env: EMAIL_SENDER)
- `email_alert_to: list[str]` - Alert recipients (env: EMAIL_ALERT_TO, comma-separated)
- `email_stock_to: list[str]` - Stock recipients (env: EMAIL_STOCK_TO, comma-separated)
- `email_alert_template: Path` - Error alert template
- `email_stock_template: Path` - Stock transfer template

**Harman Settings:**
- `harman_input_dir: Path` - EDIFACT input (derived: work_dir/harman/in)
- `harman_output_dir: Path` - EDIFACT output (derived: work_dir/harman/out)
- `harman_administration_id: int` - Odoo company ID (default: 2)
- `harman_customer_id: int` - Odoo customer ID (default: 5380)
- `harman_pricelist_id: int` - Odoo pricelist (default: 2)
- `harman_order_provider: str` - "HARMAN JBL"
- `harman_shipment_type: str` - "harman%"
- `harman_stock_supplier_name: str` - "Harman JBL"
- `harman_stock_upload_link: str` - Google Drive folder link
- `harman_workdays_for_delivery: int` - Delivery lead time (default: 2)

**Log Settings:**
- `log_file: Path` - Log filename (derived: work_dir/logs/external_order.log)
- `log_backup_count: int` - Rotation backups (default: 14)
- `log_file_level: str` - Log level (default: "DEBUG")

**Odoo Settings:**
- `odoo_base_url: str` - JSON-RPC endpoint (env: ODOO_BASE_URL)
- `odoo_database: str` - Database name (env: ODOO_DATABASE)
- `odoo_rpc_user_id: int` - RPC user ID (env: ODOO_RPC_USER_ID)
- `odoo_rpc_password: str` - RPC password (env: ODOO_RPC_PASSWORD)

**Spectrum Settings:**
- `spectrum_base_url: str` - API base URL (env: SPECTRUM_BASE_URL)
- `spectrum_harman_api_key: str` - API key (env: SPECTRUM_HARMAN_API_KEY)

**Key behavior:**
- All directories created in `__post_init__()` via `mkdir(parents=True, exist_ok=True)`
- `get_config()` returns cached Config instance via @cache decorator

---

## 7. Entry Point & Main Workflow

Located in [src/main.py](src/main.py)

**Dependency Injection & Orchestration:**

```python
def main() -> None:
    # 1. Load configuration & setup
    config: Config = get_config()
    error_store = get_error_store()
    configure_logging(...)

    # 2. Initialize service registries
    artwork_services: IRegistry[IArtworkService] = Registry[IArtworkService]()
    order_services: IRegistry[IOrderService] = Registry[IOrderService]()
    order_services.register("HARMAN JBL", HarmanOrderService())
    stock_services: IRegistry[IStockService] = Registry[IStockService]()
    stock_services.register("Harman JBL", HarmanStockService())
    use_cases: IRegistry[IUseCase] = Registry[IUseCase]()

    # 3. Create service instances and register use cases
    with requests.Session() as sale_session, requests.Session() as spectrum_session:
        artwork_services.register("Spectrum", SpectrumArtworkService(session=spectrum_session, api_key=config.spectrum_api_key))
        sale_service: ISaleService = OdooSaleService(session=sale_session)
        
        use_cases.register("NewSale", NewSaleUseCase(...))
        use_cases.register("CompletedSale", CompletedSaleUseCase(...))
        use_cases.register("StockTransfer", StockTransferUseCase(...))

        # 4. Execute all use cases
        for use_case_name, use_case in use_cases.items():
            try:
                logger.info(f"Execute use case: {use_case_name}")
                use_case.execute()
            except Exception as exc:
                error_store.add(exc)

    # 5. Send error alert if needed
    if error_store.has_errors():
        emailer = EmailSender(...)
        emailer.send(...)
```

**Execution flow:**
1. NewSaleUseCase: Create/update sales with artwork
2. CompletedSaleUseCase: Notify providers
3. StockTransferUseCase: Process stock transfers

---

## 8. Test Structure

Located in [tests/](tests/)

**Test organization:**

```
tests/
├── unit/                          # Unit tests
│   ├── test_config.py            # Config loading & defaults
│   ├── domain/                   # Domain model tests
│   │   ├── test_order.py         # Order validation & methods
│   │   ├── test_line_item.py     # LineItem creation & artwork
│   │   ├── test_ship_to.py       # ShipTo validation & normalization
│   │   ├── test_artwork.py       # Artwork file existence checks
│   │   └── test_validators.py    # Validation functions
│   ├── app/                      # Application layer tests
│   │   ├── test_odoo_auth.py     # OdooAuth validation
│   │   ├── test_stock_transfer_use_case.py
│   │   ├── test_new_sale_use_case.py
│   │   ├── test_registry.py      # Registry thread-safety
│   │   └── test_errors.py        # ErrorStore functionality
│   └── services/                 # Service unit tests
│       ├── test_render_service.py
│       ├── test_harman_order_service.py     # EDIFACT parsing
│       ├── test_harman_stock_service.py     # XML processing
│       ├── test_odoo_sale_service.py        # RPC mocking
│       ├── test_spectrum_artwork_service.py # API mocking
│       └── conftest.py           # Fixtures & mocks
├── integration/                   # Integration tests
│   ├── conftest.py               # Test fixtures
│   ├── test_main.py              # Full workflow
│   ├── test_new_sale_integration.py
│   ├── test_completed_sale_integration.py
│   ├── test_stock_transfer_integration.py
│   └── test_services_integration.py
```

**Coverage targets:**
- Aim for comprehensive unit test coverage (mock external services)
- Integration tests with real files/EDIFACT examples
- Error paths and validation thoroughly tested

**Running tests:**
```bash
uv run pytest tests/unit/ --cov=src --cov-report=html
uv run pytest tests/integration/ --cov=src
```

---

## 9. Key Design Patterns

### Hexagonal Architecture
- **Domain layer**: Pure models with no dependencies (order.py, ship_to.py, artwork.py)
- **Port layer**: Interfaces defining contracts (ports.py)
- **Adapter layer**: Service implementations (harman_*, odoo_*, spectrum_*)
- **Application layer**: Use cases orchestrating workflows

### Protocol (Interface) Segregation
- `IOrderService` composed of `IOrderReader + IOrderStore + IOrderNotifier + IArtworkServiceProvider`
- Allows implementations to focus on specific concerns
- Enables easy testing with mocks

### Thread-Safe Registry
- Generic `Registry[T]` with Lock for thread-safe get/register
- Used for service discovery throughout application

### Immutable Domain Models
- Frozen dataclasses ensure no accidental mutation
- Setter methods use `object.__setattr__()` for controlled updates
- Validation in `__post_init__()`

### Error Handling
- Per-use-case exception handling without stopping other workflows
- `ErrorStore` collects errors for batched alert email
- Custom exceptions with optional order ID context

### Configuration-Driven
- All magic numbers, paths, URLs from Config
- Environment variables override defaults
- Cached singleton instance via @cache decorator

---

## 10. External Dependencies & Integration Points

**Order/Stock Providers:**
- **Harman**: EDIFACT format (.insdes, .new, .created, .artwork, .xml files)
  - File-based: reads/writes to directory structure
  - Notifications: DESADV D96A/D99A templates

**Artwork Provider:**
- **Spectrum**: REST API
  - GET `/api/order/order-number/{remote_order_id}/`
  - GET `/api/webtoprint/{recipe_set_id}/` (ZIP download)
  - GET `/{clientHandle}/specification/{recipe_set_id}/pdf/`
  - API key in header: `SPECTRUM_API_TOKEN`

**Sales System:**
- **Odoo**: JSON-RPC 2.0
  - Models: sale.order, res.partner, product.product, delivery.carrier, res.country, res.country.state
  - Custom fields: x_remote_order_id, x_remote_order_provider, x_remote_delivery_instructions, deonet_other_company, x_sale_notified, x_serial_numbers

**Notifications:**
- **Email**: SMTP relay (redmail library)
  - Error alerts to EMAIL_ALERT_TO
  - Stock confirmations to EMAIL_STOCK_TO

---

## 11. Summary of API Changes/Evolution

This codebase represents a clean, production-ready implementation with:

1. **Strict typing**: Full type hints throughout, frozen dataclasses
2. **Validation**: All inputs validated in domain models
3. **Error context**: Custom exceptions carry order ID for better debugging
4. **Thread safety**: Registry uses locks for concurrent access
5. **Configuration**: All external settings externalized to Config
6. **Logging**: Comprehensive at debug level, clean console output
7. **Testing**: Both unit (mocked) and integration tests
8. **Documentation**: Detailed docstrings on all public methods

The architecture allows easy addition of new order/stock/artwork providers by implementing the appropriate Protocol interfaces.
