# API Specifications & External Integration Points

## 1. Odoo Integration (JSON-RPC 2.0)

### Base Configuration
```
Base URL: {ODOO_BASE_URL}/jsonrpc
Method: POST
Auth: RPC User ID + Password
```

### Authentication Fields (from OdooAuth)
```python
database: str              # ODOO_DATABASE env var
user_id: int              # ODOO_RPC_USER_ID env var
password: str             # ODOO_RPC_PASSWORD env var
```

### Generic RPC Call Structure
```python
payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "service": "object",
        "method": "execute_kw",
        "args": [
            database,           # ODOO_DATABASE
            user_id,           # ODOO_RPC_USER_ID
            password,          # ODOO_RPC_PASSWORD
            model,             # e.g., "sale.order"
            method,            # e.g., "create"
            query_data or [],  # Positional arguments
            query_options or {}, # Keyword arguments (fields, limit, etc.)
        ]
    },
    "id": counter
}
```

### API Methods Used

#### 1. Create Sale Order
```
Model: sale.order
Method: create
Params:
{
    "partner_id": customer_id,
    "partner_shipping_id": contact_id,
    "company_id": administration_id,
    "client_order_ref": order_description,
    "pricelist_id": pricelist_id,
    "order_line": [(0, 0, line_dict), ...],  # 0,0 = create new
    "state": "sale",                          # Created directly in final state
    "commitment_date": ISO date string,
    "carrier_id": carrier_id,
    "x_remote_delivery_instructions": instructions or None,
    "x_remote_order_id": remote_order_id,
    "x_remote_order_provider": order_provider,
}
Returns: (sale_id: int, sale_name: str) - tuple of (ID, Name)
Note: Sales are created in "sale" state (no separate confirm step needed)
```

#### 2. Search Sale Order
```
Model: sale.order
Method: search_read
Params (query_data):
[[
    ["company_id", "=", administration_id],
    ["x_remote_order_id", "=", remote_order_id],
    ["x_remote_order_provider", "=", order_provider],
]]
Params (query_options):
{"limit": 1}
Returns: list of dicts with id, state, etc.
```

#### 3. Update Sale
```
Model: sale.order
Method: write
Params (query_data): [[sale_id], {fields_dict}]
Returns: bool
```

#### 4. Search Completed Sales
```
Model: sale.order
Method: search_read
Params (query_data):
[[
    ["x_remote_order_provider", "=", order_provider],
    ["state", "=", "done"],
    ["x_sale_notified", "=", False],
]]
Params (query_options):
{"fields": ["id", "x_remote_order_id"]}
Returns: list of dicts with id, x_remote_order_id
```

#### 5. Mark Sale Notified
```
Model: sale.order
Method: write
Params (query_data):
[[sale_id], {"x_sale_notified": True}]
Returns: bool
```

#### 6. Search Shipping Info
```
Model: stock.move
Method: search_read
Params (query_data):
[[
    ["sale_id", "=", sale_id],
    ["state", "=", "done"],
]]
Params (query_options):
{"fields": ["picking_id", "carrier_tracking_ref"]}
Returns: list of dicts
```

#### 7. Search Serials
```
Model: stock.serial.move
Method: search_read
Params (query_data):
[[["sale_id", "=", sale_id]]]
Params (query_options):
{"fields": ["product_id", "serial"]}
Returns: list of dicts with product_id (tuple), serial
```

#### 8. Search/Create Contact (res.partner)
```
Model: res.partner
Method: create
Params:
{
    "company_id": administration_id,
    "parent_id": customer_id,
    "ref": remote_customer_id,
    "name": contact_name,
    "deonet_other_company": company_name or None,
    "type": "other",
    "is_company": True,
    "street": street1,
    "street2": street2 or None,
    "city": city,
    "state_id": state_id or None,
    "zip": postal_code,
    "country_id": country_id,
    "phone": phone,
    "email": email,
    "x_remote_order_provider": order_provider,
    "active": False,
    "portal_visible": False,
}
Returns: int (contact ID)
```

#### 9. Search Country
```
Model: res.country
Method: search_read
Params (query_data):
[[["code", "=", country_code.upper()[:2]]]]
Params (query_options):
{"fields": ["id"], "limit": 1}
Returns: list of dicts with id
```

#### 10. Search State
```
Model: res.country.state
Method: search_read
Params (query_data):
[[
    ["country_id", "=", country_id],
    ["name", "ilike", state_name],
]]
Params (query_options):
{"fields": ["id"], "limit": 1}
Returns: list of dicts with id
```

#### 11. Search Carrier
```
Model: delivery.carrier
Method: search_read
Params (query_data):
[[
    ["company_id", "=", administration_id],
    ["name", "ilike", shipment_type],
]]
Params (query_options):
{"fields": ["id"], "limit": 1}
Returns: list of dicts with id
```

#### 12. Search Products
```
Model: product.product
Method: search_read
Params (query_data):
[[["default_code", "=", product_code]]]
Params (query_options):
{"fields": ["id", "name"], "limit": 1}
Returns: list of dicts with id, name
```

### Error Response Format
```python
{
    "jsonrpc": "2.0",
    "error": {
        "code": 200,
        "message": "odoo.exceptions.AccessError",
        "data": {
            "type": "client_error",
            "arguments": ["..."],
            "message": "..."
        }
    },
    "id": counter
}
```

---

## 2. Spectrum Artwork API (REST)

### Base Configuration
```
Base URL: {SPECTRUM_BASE_URL}
Auth Header: SPECTRUM_API_TOKEN: {SPECTRUM_HARMAN_API_KEY}
Timeout: (5, 30) seconds
```

### API Endpoints

#### 1. Get Order Data
```
Method: GET
Path: /api/order/order-number/{remote_order_id}/
Response:
{
    "clientHandle": "string",
    "lineItems": [
        {
            "id": int,
            "skuQuantities": [
                {
                    "sku": "product_code",
                    "quantity": int
                }
            ],
            "recipeSetId": "recipe_id"
        }
    ]
}
```

#### 2. Get Webtoprint (Design ZIP)
```
Method: GET
Path: /api/webtoprint/{recipe_set_id}/
Response: ZIP file bytes
Content-Type: application/zip
Extraction: Files prefixed with {sale_name}_{filename}
```

#### 3. Get Placement PDF
```
Method: GET
Path: /{clientHandle}/specification/{recipe_set_id}/pdf/
Response: PDF file bytes
Content-Type: application/pdf
Save as: {sale_name}_{recipe_set_id}_placement.pdf
```

---

## 3. Camelbak Order API (REST)

### Base Configuration
```
Base URL: {SPECTRUM_BASE_URL}
Auth Header: SPECTRUM_API_TOKEN: {SPECTRUM_API_KEY}
Method: POST for order search
Timeout: (5, 30) seconds
```

### API Endpoints

#### 1. Search Orders
```
Method: POST
Path: /api/orders/search/
Authentication: Authorization header with api_key
Request Body:
{
    "lastModificationStartDate": "YYYY-MM-DD",  # Today's date
    "workflowStatuses": ["not-started"]         # Filter for new orders
}
Response: Array of order objects
```

#### 2. Order Data Structure
```
{
    "purchaseOrderNumber": "ORDER-12345",
    "userId": "USER123",
    "emailAddress": "user@example.com",
    "phoneNumber": "+1-555-0123",
    "shippingAddress": {
        "firstName": "John",
        "lastName": "Doe",
        "address1": "123 Main St",
        "address2": "Suite 100",
        "city": "Chicago",
        "state": "IL",           # or "province" for Canada
        "postalCode": "60601",
        "country": "US"
    },
    "lineItems": [
        {
            "recipeSetId": "RECIPE-001",
            "skuQuantities": [
                {
                    "sku": "SKU001",
                    "quantity": "100"
                }
            ]
        }
    ]
}
```

#### 3. Update Order Status
```
Method: PUT
Path: /api/order/status/
Request Body:
{
    "purchaseOrderNumber": "ORDER-12345",
    "lineItems": [
        {
            "recipeSetReadableId": "RECIPE-001",
            "workflowStatus": "in-progress"
        }
    ]
}
Response: Success confirmation
```

#### 4. Ship Notification
```
Method: POST
Path: /api/order/ship-notification/
Request Body:
{
    "purchaseOrderNumber": "ORDER-12345",
    "lineItems": [
        {
            "recipeSetReadableId": "RECIPE-001",
            "shipmentTracking": "TRACK-123456"
        }
    ]
}
Response: Success confirmation
```

### Key Characteristics
- **Authentication**: API token in header (SPECTRUM_API_TOKEN)
- **Order States**: new (not-started) → in-progress → shipped
- **Shipment Tracking**: Can contain multiple comma-separated tracking references
- **Multiple SKUs**: Each recipe set can have multiple SKU quantities
- **Optional Fields**: Province (Canada), address2, state (US)
- **JSON Serialization**: DateTime fields serialized using custom JSON encoder

---

## 4. Harman EDIFACT Format

### Input File Types
Located in: `{work_dir}/harman/in/`

```
*.insdes   - New EDIFACT order
*.new      - Received order
*.created  - Order created in Odoo
*.artwork  - Artwork received
*.confirmed- Order confirmed
*.json     - Persisted order state
```

### EDIFACT Segment Parsing

#### NAD Segment (Name and Address)
```
NAD + ST + [remote_customer_id] + [name1, name2, email, ...] + [phone, ...] 
    + [street1, street2, _, house_nr, ...] + city + state + postcode + country

Maps to ShipTo:
- remote_customer_id
- company_name: name1 if name2 else ""
- contact_name: name2 if name2 else name1
- email
- phone
- street1: "{street1} {house_nr}"
- street2
- city
- state
- postal_code: postcode
- country_code: country
```

#### RFF Segment (Reference)
```
RFF + [DQ, delivery_note_id] → order_data["delivery_note_id"]
RFF + [ON, remote_order_id] → order_data["remote_order_id"]
```

#### LIN Segment (Line Item)
```
LIN + line_id + "1" + [product_code, "MF"]
→ order_data["line_items"].append({
    "remote_line_id": line_id,
    "product_code": product_code
})
```

#### QTY Segment (Quantity)
```
QTY + [113, quantity, unit_of_measure]
→ order_data["line_items"][-1]["quantity"] = quantity
```

#### FTX Segment (Free Text)
```
FTX + DEL + 3 + "" + delivery_instructions
→ order_data["delivery_instructions"]

FTX + PRD + "" + "" + [location, stock_status]
→ order_data["line_items"][-1]["location"]
   order_data["line_items"][-1]["stock_status"]
```

### Output File Types
Located in: `{work_dir}/harman/out/`

```
{remote_order_id}.DESADVD96A  - Delivery notification (D96A format)
{remote_order_id}.DESADVD99A  - Delivery notification (D99A format)
HARMAN_IN05_{delivery_number}.XML - Stock receipt confirmation
```

### DESADV Template Variables
```
Provided to templates:
- interchange_control_ref: 10-digit random
- ship_date: ISO datetime
- expected_date: ISO datetime
- box_length, box_width, box_height: dimensions
- sale_name: {sale_name}
- sscc: 20-digit random SSCC code
- num_segments: dict with D96A and D99A counts
- order: original parsed order data
- shipping_info: delivery tracking info
- serials_by_line: serial numbers grouped by line
```

### File Status Transitions
```
{remote_id}.insdes
    ↓ (read_orders)
{remote_id}.NEW       (persist_order status=NEW)
    ↓ (process & create sale)
{remote_id}.CREATED   (persist_order status=CREATED)
    ↓ (download artwork)
{remote_id}.ARTWORK   (persist_order status=ARTWORK)
    ↓ (confirm sale)
{remote_id}.CONFIRMED (persist_order status=CONFIRMED)
    ↓ (completed workflow)
{remote_id}.COMPLETED (persist_order status=COMPLETED)
```

---

## 4. Harman Stock Transfer (XML)

### Input Format (DELVRY03 IDOC)
```
Location: {work_dir}/harman/in/
Filename: *in04*.xml (must contain 'in04' in filename stem)

Structure:
<?xml>
  <DELVRY03>
    <IDOC>
      <EDI_DC40>                    # Control segment
        <DOCNUM>docnum</DOCNUM>     # IDOC number
        <CREDAT>YYYYMMDD</CREDAT>   # Creation date
        <CRETIM>HHMMSS</CRETIM>     # Creation time
      </EDI_DC40>
      <E1EDL20>                     # Header segment
        <VBELN>delivery_number</VBELN>
        <E1EDL24>                   # Item segment (repeating)
          <POSNR>item_number</POSNR>
          <MATNR>product_code</MATNR>
          <LFIMG>quantity</LFIMG>
          <LGORT>storage_location</LGORT>
        </E1EDL24>
      </E1EDL20>
    </IDOC>
  </DELVRY03>
```

### Output Format (IN05 Reply)
```
Location: {work_dir}/harman/out/
Filename: HARMAN_IN05_{delivery_number}.XML

Structure:
<?xml>
  <HARMAN>
    <IDOC>
      <EDI_DC40>
        <DOCNUM>{original_docnum}</DOCNUM>
        <DIRECT>2</DIRECT>
        <INTCODE>IN05</INTCODE>
        <CREDAT>YYYY-MM-DD</CREDAT>
        <CRETIM>HH:MM:SS</CRETIM>
      </EDI_DC40>
      <E1EDL20>
        <VBELN>{delivery_number}</VBELN>
        <E1EDL24>
          <POSNR>{item_number}</POSNR>
          <MATNR>{product_code}</MATNR>
          <BATCH>CLEAR</BATCH>
          <STKSTA>{storage_location}UN</STKSTA>
          <DELQTY>{quantity}</DELQTY>
        </E1EDL24>
      </E1EDL20>
    </IDOC>
  </HARMAN>
```

### File Status Transitions
```
{id}.xml (received)
    ↓ (process)
{id}.replied (processed)
```

---

## 5. Configuration Environment Variables

```bash
# Application
WORK_DIR="/path/to/data"              # Default: ~/projects-data/external_order
SSL_VERIFY="true"                     # SSL certificate verification

# SMTP Email
SMTP_HOST="smtp-relay.gmail.com"      # SMTP server
SMTP_PORT="587"                       # SMTP port
EMAIL_SENDER="bot@example.com"        # From address
EMAIL_ALERT_TO="admin@example.com,support@example.com"   # Alert recipients
EMAIL_STOCK_TO="warehouse@example.com"                    # Stock recipients

# Odoo
ODOO_BASE_URL="https://odoo.example.com"    # JSON-RPC endpoint
ODOO_DATABASE="production"                   # Database name
ODOO_RPC_USER_ID="1"                        # RPC user ID
ODOO_RPC_PASSWORD="secret_password"         # RPC password

# Spectrum
SPECTRUM_BASE_URL="https://api.spectrum.example.com/"  # API base URL
SPECTRUM_HARMAN_API_KEY="api_key_token"                       # API token
```

---

## 6. Data Validation Rules

### Order (Order.py)
- administration_id: positive integer
- customer_id: positive integer
- pricelist_id: positive integer
- order_provider: non-empty string (normalized)
- remote_order_id: non-empty string (normalized)
- shipment_type: non-empty string (normalized)
- description: non-empty string (normalized)
- delivery_instructions: optional (default "")
- ship_to: ShipTo instance required
- line_items: non-empty list of LineItem instances

### ShipTo (ship_to.py)
- remote_customer_id: non-empty string
- company_name: optional (default "")
- contact_name: non-empty string
- email: valid email format (normalized lowercase)
- phone: digits + valid chars (+-() )
- street1: non-empty string
- street2: optional (default "")
- city: non-empty string
- state: optional (default "")
- postal_code: non-empty string (normalized uppercase)
- country_code: 2-letter ISO code (normalized uppercase)

### LineItem (line_item.py)
- line_id: non-empty string (normalized)
- product_code: non-empty string (normalized)
- quantity: positive integer
- artwork: optional Artwork instance or None

### Artwork (artwork.py)
- artwork_id: non-empty string
- artwork_line_id: non-empty string
- design_url: non-empty string
- design_paths: non-empty list of Path objects (must exist)
- placement_url: non-empty string
- placement_path: Path object (must exist)

### OdooAuth (odoo_auth.py)
- database: non-empty string
- user_id: positive integer
- password: non-empty string

---

## 7. Error Handling & Resilience

### HTTP Error Context Wrapping

All HTTP errors (`requests.HTTPError`) from external services are caught and wrapped with domain-specific context to preserve order/operation information:

```python
# In OdooSaleService
try:
    response = self.session.post(f"{self.base_url}/jsonrpc", json=payload)
    response.raise_for_status()
except requests.HTTPError as http_err:
    # Wrap with domain context
    raise SaleError(
        f"Odoo RPC failed for order {order.remote_order_id}: "
        f"Status {response.status_code}, Response: {response.text}"
    ) from http_err

# In SpectrumArtworkService
try:
    response = self.session.get(f"{self.base_url}/api/order/{recipe_set_id}/")
    response.raise_for_status()
except requests.HTTPError as http_err:
    raise ArtworkError(
        f"Failed to fetch artwork for order {order.remote_order_id}: {http_err}"
    ) from http_err

# In HarmanOrderService
try:
    response = self.session.get(url)
    response.raise_for_status()
except requests.HTTPError as http_err:
    raise OrderError(
        f"Failed to reach Harman for order {order.remote_order_id}: {http_err}"
    ) from http_err
```

**Benefits:**
- Preserves stack trace (`from http_err` maintains exception chain)
- Adds order/operation context for debugging
- Enables targeted error handling based on service type
- Makes error emails more actionable

### Exception Hierarchy

```
Exception
├─ SaleError                          # Odoo sale operations
├─ ArtworkError                       # Spectrum artwork service
├─ OrderError                         # Order processing, EDIFACT parsing
└─ (built-in exceptions)
   ├─ ValueError                      # Validation failures
   ├─ requests.HTTPError              # HTTP failures (wrapped above)
   └─ other exceptions
```

### Error Collection & Reporting

#### Per-Use-Case Error Isolation
Each use case executes with per-item error handling:

```python
# In use cases
for order in orders:
    try:
        # Process order
    except Exception as exc:
        error_store.add(exc)            # Collect error
        logger.error("Order failed: %s", exc)  # Log with context
        # Continue to next order - don't stop execution
```

#### ErrorStore (Singleton)

```python
from src.app.errors import get_error_store

error_store = get_error_store()

# Add errors during operation
if artwork_urls_missing:
    error_store.add(ArtworkError("Artwork not found for line items"))

# Check if errors occurred
if error_store.has_errors():
    # Get data for error email template
    email_data = error_store.get_render_email_data()
    # email_data = {
    #     "errors": ["Error 1", "Error 2", ...],
    #     "error_count": 2,
    #     "timestamp": "2024-01-15 10:30:45"
    # }
```

### Error Email Contents

When errors are collected during execution, an alert email is sent with:
```python
{
    "error_count": int,
    "errors": list[str],          # Formatted error messages with context
    "timestamp": "YYYY-MM-DD HH:MM:SS",
    "hostname": "server-name"
}
```

**Email Template:** `error_alert.html` (rendered with above data)

### Resilience Patterns

#### 1. Multi-Provider Continuation
```python
# In NewSaleUseCase
for order_service_name, order_service in order_services.items():
    try:
        for order in order_service.read_orders():
            # Process order
    except Exception as exc:
        error_store.add(exc)
        # Continue to next provider even if this one fails
```

#### 2. Multi-Order Continuation
```python
# Within a provider's workflow
for order in orders:
    try:
        create_sale(order)
        get_artwork(order)
        confirm_order(order)
    except Exception as exc:
        error_store.add(exc)
        # Continue to next order
```

#### 3. Multi-Step Continuation Without Rollback
```python
# In CompletedSaleUseCase
try:
    notify_data = order_service.get_notify_data(order)
    order_service.notify_completed_sale(order, notify_data)  # Step 1
    sale_service.mark_sale_notified(sale_id)                 # Step 2
    order_service.persist_order(order, OrderStatus.COMPLETED) # Step 3
except Exception as exc:
    error_store.add(exc)
    # If step 1 fails: no mark_sale_notified, no persist
    # If step 2 fails: sale marked but persist not called
    # If step 3 fails: sale marked (no rollback of step 2)
```

### Response Codes & Handling

#### Odoo RPC Error Response
```python
{
    "jsonrpc": "2.0",
    "error": {
        "code": 200,
        "message": "odoo.exceptions.AccessError",
        "data": {
            "type": "client_error",
            "arguments": ["..."],
            "message": "..."
        }
    },
    "id": counter
}
```

#### Spectrum API Error Response
```python
# HTTP 4xx/5xx status codes trigger requests.HTTPError
# Wrapped as ArtworkError with order context
```

#### Handling Patterns

**Retriable Errors (temporary failures):**
- Network timeouts
- 429 Too Many Requests
- 503 Service Unavailable
→ Currently: Collected in ErrorStore, reported in alert email (no automatic retry)
→ Future: Could implement exponential backoff

**Non-Retriable Errors (data problems):**
- 404 Not Found
- 400 Bad Request
- 401 Unauthorized
→ Collected and reported, manual investigation needed

### Data Response Formats

See Section 6 above for complete field specifications and validation rules.

---

## 8. Error Response Codes & Handling (Legacy)

### Exception Hierarchy
```
Exception
├─ BaseError (order_id context)
│  ├─ ArtworkError
│  ├─ InsdesError
│  ├─ NotifyError
│  └─ SaleError
└─ (other exceptions)
```

### Caught & Collected Errors
All errors in use case execution are:
1. Caught at per-order level
2. Added to ErrorStore via `error_store.add(exc)`
3. Logged with context
4. Execution continues to next order
5. After all use cases, if errors → send alert email

### Error Email Contents
```python
{
    "error_count": int,
    "errors": list[str],          # Formatted tracebacks
    "timestamp": "YYYY-MM-DD HH:MM:SS",
    "company_name": "Deonet Production B.V."
}
```
