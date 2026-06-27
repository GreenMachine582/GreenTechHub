# Addon System

GreenTechHub uses a plugin-style architecture where all feature code lives under `addons/`. New apps are discovered at startup with **zero changes to settings**.

## How Discovery Works

Three scan loops run at import time — two in `server/settings.py` and one in `server/urls.py`:

**`server/settings.py` — INSTALLED_APPS:**
```python
ADDONS_DIR = BASE_DIR / "addons"
addon_paths = [p for p in ADDONS_DIR.iterdir() if p.is_dir() and (p / "apps.py").exists()]
ADDONS_APPS = [f"addons.{p.name}" for p in sorted(addon_paths, key=lambda p: p.name.lower())]
INSTALLED_APPS = ADDONS_APPS + INSTALLED_APPS
```

**`server/settings.py` — TEMPLATES DIRS:**
```python
"DIRS": [str(p / "templates") for p in addon_paths if (p / "templates").exists()]
```

**`server/settings.py` — STATICFILES_DIRS:**
```python
STATICFILES_DIRS = [str(p / "static") for p in addon_paths if (p / "static").exists()]
```

**`server/settings.py` — Context processors:**
```python
[f"addons.{app.name}.context_processors.default_context"
 for app in scandir(ADDONS_DIR)
 if app.is_dir() and (ADDONS_DIR / app.name / "context_processors.py").exists()]
```

**`server/urls.py` — URL patterns:**
```python
urlpatterns = [
    path('', include(f"addons.{app.name}.urls"))
    for app in scandir(settings.ADDONS_DIR)
    if app.is_dir() and (settings.ADDONS_DIR / app.name / "urls.py").exists()
]
```

## What Makes an Addon

The **minimum** required file is `apps.py` containing an `AppConfig`:

```python
# addons/myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.myapp"   # must match the directory name exactly

    def ready(self):
        from . import signals  # import signals here to connect them
```

## Optional Files and Their Effects

| File/Dir | Effect when present |
|---|---|
| `apps.py` | **Required.** Registers as `addons.<dirname>` in `INSTALLED_APPS` |
| `urls.py` | Auto-included at root URL conf (no path prefix added) |
| `templates/` | Directory added to Django template search path |
| `static/` | Directory added to `STATICFILES_DIRS` |
| `context_processors.py` with `default_context(request)` | Auto-wired into `TEMPLATES["OPTIONS"]["context_processors"]` |
| `signals.py` | Should be imported in `AppConfig.ready()` to connect receivers |
| `migrations/` | Django discovers this automatically once the app is installed |
| `admin.py` | Django admin auto-discovers this |

## Step-by-Step: Creating a New Addon

1. **Create the directory:**
   ```
   addons/myapp/
   ```

2. **Create `apps.py`** (minimum viable addon):
   ```python
   from django.apps import AppConfig

   class MyAppConfig(AppConfig):
       default_auto_field = "django.db.models.BigAutoField"
       name = "addons.myapp"

       def ready(self):
           from . import signals
   ```

3. **Create `__init__.py`** (empty is fine):
   ```
   addons/myapp/__init__.py
   ```

4. **Create `models.py`** if the app needs database models. Run migrations after:
   ```bash
   python server.py makemigrations myapp
   python server.py migrate
   ```

5. **Create `urls.py`** with URL patterns. Each addon owns its own path prefixes:
   ```python
   from django.urls import path
   from . import views

   urlpatterns = [
       path("myapp/things/", views.ThingListView.as_view(), name="myapp-thing-list"),
   ]
   ```

6. **Create `views.py`** with your views.

7. **Create `templates/`** directory for HTML templates (no namespacing needed — the addon dirname isn't a namespace here, but be careful about name collisions with other addons).

8. **Create `static/`** directory for CSS/JS/images if needed.

9. **Create `context_processors.py`** if you need template globals (the function MUST be named `default_context`):
   ```python
   def default_context(request):
       return {"my_global": "value"}
   ```

10. **Create `signals.py`** for Django signal receivers. Import it in `AppConfig.ready()`.

11. **Restart the dev server.** The app is now discovered automatically.

## Naming Conventions

- **Directory name:** `lowercase_underscore` (e.g., `modal_forms`, `querybuilder`)
- **AppConfig class:** `TitleCaseConfig` or `TitleCaseAppConfig`
- **`name` in AppConfig:** always `addons.<dirname>` — must match the filesystem exactly
- **URL names:** prefix with app name to avoid collisions (`pyfinbot-stock-list`, not `stock-list`)

## Cross-App Imports

Import from other addons using the full dotted path:

```python
from addons.base.models import Profile
from addons.base.utils.mixins import AjaxAwareLoginRequiredMixin
from addons.authentication.models import User, Role, GroupProfile
from addons.authentication.mixins import LoginRequiredMixin
from addons.microservice.views import BaseMicroserviceFormView
```

Avoid relative imports that assume apps are siblings in the same package — they are, but it makes dependency direction unclear.

## App Ordering

Apps are loaded in **alphabetical order** (case-insensitive):

1. `authentication`
2. `base`
3. `microservice`
4. `modal_forms`
5. `pyfinbot`
6. `querybuilder`

**Implications:**
- `base` signals that create Profile rows fire after `authentication` creates Users — this is fine because `post_save` receivers are connected at `ready()` time, not at startup sequence time
- If your app's `AppConfig.ready()` accesses models from another addon, Django guarantees all models are registered before any `ready()` is called, so cross-app model access in `ready()` is safe

## Migrations

Each addon has its own `migrations/` directory. Django discovers these automatically.

**Cross-app ForeignKeys in migrations** use the `addons_<appname>` label format:
```python
# In a migration for addons.pyfinbot referencing addons.authentication
migrations.AddField(
    model_name="somemodel",
    name="user",
    field=models.ForeignKey("authentication.User", ...),
    # Django resolves "authentication.User" to "addons.authentication.User" via AUTH_USER_MODEL
)
```

For `AUTH_USER_MODEL` ForeignKeys, always use `settings.AUTH_USER_MODEL`:
```python
from django.conf import settings
models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
```

## The `base` Addon as a Dependency

Almost every other addon depends on `base`. It provides:

- **`base.html`** — master template; extend this in all feature templates
- **`LoginRequiredMixin`** (in `addons.authentication.mixins`) — AJAX/HTMX-aware login check
- **`AjaxAwareLoginRequiredMixin`** (in `addons.base.utils.mixins`) — returns JSON 401 for AJAX/HTMX
- **`AjaxOnlyMixin`** — restricts views to AJAX/HTMX requests
- **Bootstrap widget patching** — all Django form widgets get Bootstrap classes globally
- **`FieldRenderer`** — Bootstrap 5 form field renderer wired in `BOOTSTRAP5` settings
- **Context processor** — injects `site_name`, `site_domain`, `meta_description`, `meta_keywords` into all templates

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `name = "myapp"` in AppConfig | App not discovered or wrong migrations | Change to `name = "addons.myapp"` |
| `context_processors.py` with wrong function name | Template context not injected | Rename function to exactly `default_context` |
| Forgot `makemigrations` | `OperationalError: no such table` | Run `python server.py makemigrations <appname>` |
| Missing `default_auto_field` | Migration warnings | Add `default_auto_field = "django.db.models.BigAutoField"` to AppConfig |
| Signals not connected | Signal receivers never fire | Import `signals` module in `AppConfig.ready()` |
| Template name collision | Wrong template rendered | Prefix template filenames or use subdirectory `templates/myapp/thing.html` |
| Relative import across addons | `ImportError` or circular import | Use absolute imports: `from addons.base.models import ...` |
