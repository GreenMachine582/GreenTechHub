# Microservice Pattern

Django acts as a UI gateway — it does not own or store most application data. Data lives in external microservices accessible via HTTP. This file documents how to wire, call, and build CRUD interfaces for those services.

## Concept

```
Browser ──→ Django (UI + auth) ──→ Microservice (data + business logic)
                 ▲
           MicroserviceClient
           (cached HTTP session)
```

The `Microservice` DB row is the registry. It maps a stable `prefix` (e.g., `"pyfinbot"`) to a `base_url` (e.g., `http://pyfinbot:8001/`). The prefix is the key used in all code.

---

## Registering a Microservice

Go to `/admin/microservice/microservice/add/` and fill in:

| Field | Example | Notes |
|---|---|---|
| `name` | `PyFinBot` | Human-readable display name |
| `prefix` | `pyfinbot` | Must match the string used in `service_prefix` class attr |
| `base_url` | `http://pyfinbot:8001/` | Include trailing slash |
| `version` | `1.0` | Optional; for display |
| `is_active` | ✓ | Must be True for clients to connect |

The microservice **must** be in the DB before any view using it is accessed. `MicroserviceClient.forPrefix()` raises `MicroserviceError` if no active service is found.

---

## URL Construction

`Microservice.buildUrl(path)` constructs the full request URL:

```python
urljoin(base_url.rstrip('/'), '/api/' + path.lstrip('/'))

# Examples:
buildUrl("/stocks/")           # → http://pyfinbot:8001/api/stocks/
buildUrl("transactions/42/")   # → http://pyfinbot:8001/api/transactions/42/
```

The `/api/` prefix is always inserted between `base_url` and `path`. This is a convention — all microservices are expected to serve their API under `/api/`.

---

## MicroserviceClient

**File:** `addons/microservice/services/client.py`

A thread-safe HTTP client with TTL-based caching per service prefix.

**Getting a client:**
```python
from addons.microservice.services.client import MicroserviceClient

client = MicroserviceClient.forPrefix("pyfinbot")
```

**Making a request:**
```python
resp = client.request(
    path="/stocks/",
    method="GET",         # GET, POST, PUT, PATCH, DELETE
    user=request.user,    # adds X-User-ID header automatically
    params={"active": True},  # query string
    json={"symbol": "AAPL"},  # request body (JSON-serialised)
    extra_headers={},     # merged with defaults
)
resp.json()  # → {"items": [...]}
```

**Caching behaviour:**
- TTL: 5 minutes per client
- Max 2 clients per prefix at once
- On `RequestException`: client calls `deregisterClient()` and raises `MicroserviceError`
- Thread-safe via `threading.RLock`

**Error handling:**
- `MicroserviceError` is raised for network errors, non-2xx responses with a `"detail"` key, or unexpected exceptions
- `validateJSONResponse(resp_json)` checks for `{"detail": "..."}` error responses from the microservice

---

## MicroserviceMixin

**File:** `addons/microservice/mixins.py`

Add to any view to get access to the cached client:

```python
from addons.microservice.mixins import MicroserviceMixin

class MyView(LoginRequiredMixin, MicroserviceMixin, TemplateView):
    service_prefix = "pyfinbot"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client = self.getClient()  # → MicroserviceClient
        resp = client.request("/stocks/", user=self.request.user)
        ctx["stocks"] = resp.json().get("items", [])
        return ctx
```

`self.getClient()` calls `MicroserviceClient.forPrefix(self.service_prefix)`.

---

## Base View Classes

All four live in `addons/microservice/views.py`. They all extend `LoginRequiredMixin` and `MicroserviceMixin`.

### BaseMicroserviceListView

Fetches a list from the microservice and passes it to a template.

**Required class attributes:**
```python
service_prefix = "pyfinbot"
list_path = "/stocks/"          # GET → expects {"items": [...]}
template_name = "stock-list.html"
```

**Optional:**
```python
context_object_name = "records"  # default; key used in template context
```

**What it does:** calls `GET list_path`, extracts `response.json()["items"]`, puts it in context as `context_object_name`. On `MicroserviceError`, shows a `messages.error()` and returns an empty list.

### BaseMicroserviceFormView

Create or update a record via the microservice. Presence of `record_id` URL kwarg determines mode.

**Required class attributes:**
```python
service_prefix = "pyfinbot"
create_path = "/stocks/"         # POST here to create
update_path = "/stocks/{id}/"    # GET here for initial data; PUT here to update
form_class = StockForm
template_name = "stock-form.html"
success_url = reverse_lazy("pyfinbot-stock-list")
```

**URL kwarg:** must be `record_id` (not `pk`):
```python
path("myapp/thing/form/<int:record_id>/", MyFormView.as_view(), name="myapp-thing-form"),
```

**Create mode** (no `record_id`): POST form → `POST create_path` with JSON body

**Update mode** (`record_id` present):
1. `GET update_path.format(id=record_id)` → populate form initial data
2. POST form → `PUT update_path.format(id=record_id)` with JSON body

**Hook: `transform_initial(initial: dict) -> dict`**
Override to reshape the microservice's GET response before it populates the form. Use this when the API shape doesn't match the form field names:
```python
def transform_initial(self, initial):
    stock = (initial or {}).get("stock") or {}
    initial = dict(initial)
    initial["stock_symbol"] = stock.get("symbol", "")
    return super().transform_initial(initial)
```

**Hook: `transform_payload(cleaned_data: dict) -> dict`**
Override to reshape `form.cleaned_data` before it's sent to the microservice. Use this to remove UI-only fields or calculated read-only fields:
```python
def transform_payload(self, cleaned_data):
    data = dict(cleaned_data)
    data.pop("stock_symbol", None)   # UI helper, not needed by API
    data.pop("total_value", None)    # calculated by API, not sent
    return super().transform_payload(data)
```

**Type coercion:** `_makeJsonable()` converts `Decimal` → `float` and `date`/`datetime` → ISO string before JSON serialisation.

### BaseMicroserviceDeleteView

DELETE with AJAX modal confirmation.

**Required class attributes:**
```python
service_prefix = "pyfinbot"
delete_path = "/stocks/{id}/"   # {id} is replaced with record_id URL kwarg
success_url = reverse_lazy("pyfinbot-stock-list")
```

**Optional modal customisation:**
```python
confirm_template_name = "modal_forms/confirm_modal.html"
confirm_title = "Delete Stock"
confirm_message = "This will permanently remove this stock."
submit_label = "Delete permanently"
submit_class = "btn-danger"           # Bootstrap button class
header_class = "bg-warning text-white"
icon = "fas fa-triangle-exclamation"
```

**AJAX contract:**
- `GET` (AJAX only): renders the modal confirm HTML fragment
- `POST` (AJAX): sends `DELETE delete_path` to microservice, returns:
  - Success: `{"ok": true, "redirect_url": "/pyfinbot/stock/list/"}`
  - Failure: `{"ok": false, "error": "error message"}` with HTTP 400
- `GET` (non-AJAX): returns HTTP 405 (not allowed)
- `POST` (non-AJAX): performs delete, redirects with `messages.success()` or `messages.error()`

### BaseMicroserviceActionView

Fire-and-forget action (no form, no confirmation). Only handles `POST`.

**Required class attributes:**
```python
service_prefix = "pyfinbot"
action_path = "/stocks/sync/{market}"   # URL kwargs are formatted in via str.format(**kwargs)
```

**Optional:**
```python
method = "POST"              # HTTP method to use (default: POST)
success_url = None           # fallback: HTTP_REFERER or "/"
success_message = "Action completed successfully."
failure_message = "Action failed."
ajax_reload = True           # AJAX response includes "reload": true
```

**Hooks:**
```python
def build_payload(self, request, **kwargs) -> dict | None:
    # Return dict to send as JSON body, or None for no body
    return None

def extra_headers(self, request, **kwargs) -> dict:
    return {}

def transform_response(self, resp) -> Any:
    # Shape the data returned in the AJAX "data" key
    return resp.json()
```

**AJAX contract:**
- Success: `{"ok": true, "data": {...}, "reload": true}`
- Failure: `{"ok": false, "error": "error message"}` with HTTP 400

---

## The Proxy Endpoint

```
/api/<service>/<path>
```

Registered in `addons/microservice/urls.py`. Handled by `MicroserviceProxyView` (DRF `APIView`, JWT authenticated).

Forwards the raw HTTP request (method, headers, body, query params) to the active microservice with the given prefix. Used by browser-side JavaScript to call microservices directly without going through a Django view.

Example: `GET /api/pyfinbot/stocks/` → `GET http://pyfinbot:8001/api/stocks/`

Requires a valid JWT token (`Authorization: Bearer <token>`).

---

## Step-by-Step: Add a New CRUD Feature

**Scenario:** Add a Portfolio model backed by a microservice.

1. **Register the microservice** in `/admin/microservice/microservice/add/` (or reuse `pyfinbot` if it's the same service).

2. **Create form class** in `addons/myapp/forms.py`. Use `django.forms.Form`, not `ModelForm` — there's no local model:
   ```python
   from django import forms

   class PortfolioForm(forms.Form):
       name = forms.CharField(max_length=100)
       description = forms.CharField(widget=forms.Textarea, required=False)
   ```

3. **Create views** in `addons/myapp/views.py`:
   ```python
   from django.urls import reverse_lazy
   from addons.microservice.views import (
       BaseMicroserviceListView, BaseMicroserviceFormView, BaseMicroserviceDeleteView
   )
   from .forms import PortfolioForm

   class PortfolioListView(BaseMicroserviceListView):
       service_prefix = "myservice"
       list_path = "/portfolios/"
       template_name = "portfolio-list.html"

   class PortfolioFormView(BaseMicroserviceFormView):
       service_prefix = "myservice"
       create_path = "/portfolios/"
       update_path = "/portfolios/{id}/"
       form_class = PortfolioForm
       template_name = "portfolio-form.html"
       success_url = reverse_lazy("myapp-portfolio-list")

   class PortfolioDeleteView(BaseMicroserviceDeleteView):
       service_prefix = "myservice"
       delete_path = "/portfolios/{id}/"
       success_url = reverse_lazy("myapp-portfolio-list")
   ```

4. **Create `addons/myapp/urls.py`:**
   ```python
   from django.urls import path
   from . import views

   urlpatterns = [
       path("myapp/portfolio/list/", views.PortfolioListView.as_view(), name="myapp-portfolio-list"),
       path("myapp/portfolio/form/", views.PortfolioFormView.as_view(), name="myapp-portfolio-form"),
       path("myapp/portfolio/form/<int:record_id>/", views.PortfolioFormView.as_view(), name="myapp-portfolio-form"),
       path("myapp/portfolio/delete/<int:record_id>/", views.PortfolioDeleteView.as_view(), name="myapp-portfolio-delete"),
   ]
   ```

5. **Ensure `addons/myapp/apps.py`** exists with `name = "addons.myapp"` — the URL file won't be picked up otherwise.

6. **Create templates** in `addons/myapp/templates/`:
   - `portfolio-list.html` — extend `base.html`; use `{{ records }}` for the data
   - `portfolio-form.html` — extend `base.html`; render `{{ form }}` with Bootstrap

7. **Test** by navigating to `/myapp/portfolio/list/`. If the microservice isn't reachable, you'll see a `messages.error()` banner — check the DB registration and network.

---

## pyfinbot as Reference Implementation

**Simple example — `StockFormView`** (`addons/pyfinbot/views.py`):
```python
class StockFormView(BaseMicroserviceFormView):
    form_class = StockForm
    template_name = "stock-form.html"
    success_url = reverse_lazy("pyfinbot-stock-list")
    service_prefix = "pyfinbot"
    create_path = "/stocks/"
    update_path = "/stocks/{id}/"
```
No transform hooks needed — the form fields match the API fields directly.

**Complex example — `TransactionFormView`** (same file):
```python
class TransactionFormView(BaseMicroserviceFormView):
    # ... standard attrs ...

    def transform_initial(self, initial):
        # API returns nested: {"stock": {"symbol": "AAPL", "market": "NASDAQ"}}
        # Form needs flat fields: stock_symbol, stock_market, stock_name
        stock = (initial or {}).get("stock") or {}
        initial = dict(initial or {})
        initial.update({
            "stock_symbol": stock.get("symbol") or "",
            "stock_market": stock.get("market") or "",
            "stock_name": stock.get("name") or "",
        })
        return super().transform_initial(initial)

    def transform_payload(self, cleaned_data):
        data = dict(cleaned_data)
        # Remove UI-only helpers (API doesn't want them)
        for k in ("stock_symbol", "stock_market", "stock_name"):
            data.pop(k, None)
        # Remove calculated read-only fields (API computes these)
        for k in ("total_value", "cost"):
            data.pop(k, None)
        return super().transform_payload(data)
```

---

## Error Handling

`MicroserviceError` (defined in `addons/microservice/exceptions.py`) is raised when:
- Network connection fails (`RequestException`)
- Microservice returns a response with a `"detail"` key (API error)
- No active microservice found for the prefix
- Unexpected exception during request

All four base view classes catch `MicroserviceError` and display a `messages.error()` to the user. The view continues rendering (shows an empty list, re-renders form with error) rather than raising an HTTP 500.

For custom views using `MicroserviceMixin` directly, wrap calls in try/except:
```python
from addons.microservice.exceptions import MicroserviceError

try:
    resp = self.getClient().request("/my/path/", user=request.user)
except MicroserviceError as e:
    messages.error(request, f"Service unavailable: {e}")
    return redirect("fallback-url")
```

---

## Tabulator Integration

List views in pyfinbot use Tabulator.js for interactive tables. The pattern:

1. View sets `ctx["columns"]` (Tabulator column config as a list of dicts)
2. View sets `ctx["template_columns"]` (columns that use HTML templates)
3. Template reads `ctx["columns"]` and serialises to JSON for Tabulator's `columns` option
4. Tabulator fetches data via AJAX using the microservice proxy URL (`/api/<service>/<path>`)

Example from `StockListView`:
```python
ctx["columns"] = [
    {"title": "Symbol", "field": "symbol", "sorter": "string", "headerFilter": "input"},
    {"title": "Actions", "field": "actions", "hozAlign": "center", "headerSort": False},
]
ctx["template_columns"] = [
    {"field": "actions", "templateId": "stock-action-template"},
]
```

The `list_path` attr is exposed to the template via `ctx["view"]` (Django's `TemplateView` adds `view` to context automatically) for Tabulator's AJAX URL.
