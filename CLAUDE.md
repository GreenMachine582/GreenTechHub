# GreenTechHub — AI Context

## Project Overview

**GreenTechHub** is a Django 5.2 web platform running on PostgreSQL, served via Gunicorn in Docker, deployed to a homelab through a Cloudflare Tunnel.

- **Entry point:** `server.py` (this is manage.py — NOT `manage.py`). All commands: `python server.py runserver`, `python server.py migrate`, etc.
- **Settings module:** `server.settings` (`DJANGO_SETTINGS_MODULE=server.settings`)
- **All feature code lives in `addons/`** — six apps auto-discovered at startup
- No Celery, no custom management commands, no async workers
- Frontend: Bootstrap 5 + vanilla JS (modular ESM); Tabulator.js for data tables

## Directory Layout

```
GTH/
  server.py                   ← Django entry point (replaces manage.py)
  server/                     ← Django project package
    settings.py               ← Addon auto-discovery lives here
    urls.py                   ← Auto-includes all addon urls.py at root
    wsgi.py
    logging_config.py
  addons/                     ← All feature apps
    authentication/           ← Custom User, Role, GroupProfile; allauth customisation
    base/                     ← Profile, avatar, mixins, widgets, renderers, core templates/static
    microservice/             ← Microservice model, MicroserviceClient, base CRUD views
    modal_forms/              ← Reusable modal infrastructure (FormModalView, DeleteConfirmModalView)
    pyfinbot/                 ← Stock/transaction UI — reference implementation of microservice pattern
    querybuilder/             ← QueryBuilderWidget form widget
  docs/                       ← Extended documentation (see pointers below)
  docker-compose.yml          ← Services: db (PostgreSQL 16) + greentechhub (app)
  Dockerfile                  ← Python 3.14-slim; Gunicorn entry point
  setup.sh                    ← Deployment script (git pull → docker compose → migrate → collectstatic)
  requirements.txt
  .github/workflows/
    django_tests.yml          ← CI: runs on non-main branches
    server_deployment.yml     ← CD: runs on push to main via Cloudflare Tunnel SSH
```

## Addon Auto-Discovery

This is the most important architectural concept. Adding a new directory under `addons/` with an `apps.py` is all it takes to register a new app — no changes to settings required.

**Five auto-discovery mechanisms in `server/settings.py` and `server/urls.py`:**

| Mechanism | Trigger | Effect |
|---|---|---|
| `INSTALLED_APPS` | `addons/<name>/apps.py` exists | App `addons.<name>` prepended, sorted alphabetically |
| `TEMPLATES["DIRS"]` | `addons/<name>/templates/` exists | Directory added to template search path |
| `STATICFILES_DIRS` | `addons/<name>/static/` exists | Directory added to static file collection |
| Context processors | `addons/<name>/context_processors.py` exists | `addons.<name>.context_processors.default_context` wired in |
| Root URLs | `addons/<name>/urls.py` exists | `include("addons.<name>.urls")` at root path (no prefix added) |

**Critical gotchas:**
- The context processor function **must** be named `default_context` — any other name is silently ignored
- App labels use the `addons.` prefix — use `addons.authentication`, not `authentication`
- Apps load in **alphabetical order** — `authentication` before `base` before `microservice`
- Addon URLs are included at the **root level** — each addon picks its own path prefix

See `docs/addon-system.md` for step-by-step instructions and common mistakes.

## Models Quick Reference

| Model | App | Key Fields | Notes |
|---|---|---|---|
| `User` | authentication | `role` FK → Role | Extends AbstractUser; `AUTH_USER_MODEL` |
| `Role` | authentication | `name`, `permissions` M2M, `groups` M2M | Bundles multiple Groups |
| `GroupProfile` | authentication | `group` OneToOne, `code_name`, `description` | Extends django `Group` with a stable slug |
| `Profile` | base | `avatar` (private), `avatar_url`, `avatar_source` | OneToOne to User; auto-created on User save |
| `Microservice` | microservice | `prefix`, `base_url`, `is_active` | Registry for external services; admin-managed |

**ER summary:** `User →(FK)→ Role →(M2M)→ Group ←(OneToOne)← GroupProfile` and `User ←(OneToOne)← Profile`

Always use `get_user_model()` or `settings.AUTH_USER_MODEL` — never `from django.contrib.auth.models import User`.

See `docs/models.md` for full field lists, methods, and signal chain.

## Auth & Role System

- `AUTH_USER_MODEL = "authentication.User"` — custom User with `role` FK
- **`user.hasGroups("code_name")`** checks both direct `user.groups` AND groups inherited via `user.role`. Using raw `user.groups.filter(...)` misses role-inherited groups.
- `GroupProfile.code_name` is the stable slug identifier for a group (auto-generated from group name)
- REST access check: `POST /api/access-check/` with `{"group": "code_name"}`
- Allauth: email + username login, mandatory email verification, Google + GitHub OAuth
- JWT: `POST /api/token/` and `POST /api/token/refresh/` (simplejwt); used for API-to-API auth
- Superuser auto-created on `post_migrate` if `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD` env vars set

See `docs/auth-roles.md` for full allauth config, signal chain, and OAuth setup.

## Microservice Pattern

Django acts as a UI gateway; data lives in external microservices. A `Microservice` DB row maps a `prefix` to a `base_url`. Register services in `/admin/`.

**Four base view classes** in `addons/microservice/views.py`:

| View Class | Use for | Required class attrs |
|---|---|---|
| `BaseMicroserviceListView` | Fetch + display list | `service_prefix`, `list_path`, `template_name` |
| `BaseMicroserviceFormView` | Create or update record | `service_prefix`, `create_path`, `update_path`, `form_class`, `template_name`, `success_url` |
| `BaseMicroserviceDeleteView` | Delete with modal confirm | `service_prefix`, `delete_path`, `success_url` |
| `BaseMicroserviceActionView` | Fire-and-forget action | `service_prefix`, `action_path` |

URL kwarg `record_id` (not `pk`) switches FormView between create and update. See `pyfinbot/views.py` for the canonical reference implementation.

See `docs/microservice-pattern.md` for the full CRUD recipe and class reference.

## URL Summary

| Pattern | Name | Notes |
|---|---|---|
| `/` | `root-redirect` | Redirects to `home` |
| `/home/` | `home` | Homepage |
| `/users/profile/` | `users-profile` | User profile page |
| `/me/avatar/` | `serve-my-avatar` | Private; login required |
| `/logout/` | `logout` | |
| `/account/delete/` | `users-delete-account` | Modal |
| `/accounts/password/set/modal/` | `password-set-modal` | Modal |
| `/accounts/password/change/modal/` | `password-change-modal` | Modal |
| `/accounts/password/reset/modal/` | `password-reset-modal` | Modal |
| `/account/connections/remove/<pk>/` | `users-delete-connection-confirm` | Modal |
| `/account/connections/remove/<pk>/do/` | `users-remove-connection` | POST |
| `/api/token/` | `token_obtain_pair` | JWT; simplejwt |
| `/api/token/refresh/` | `token_refresh` | JWT |
| `/api/userinfo/` | `userinfo` | JWT auth; POST |
| `/api/access-check/` | `access_check` | JWT auth; POST |
| `/api/<service>/<path>` | `microservice-proxy` | JWT auth; forwards to microservice |
| `/pyfinbot/stock/list/` | `pyfinbot-stock-list` | |
| `/pyfinbot/stock/form/` | `pyfinbot-stock-form` | create |
| `/pyfinbot/stock/form/<record_id>/` | `pyfinbot-stock-form` | update |
| `/pyfinbot/stock/delete/<record_id>/` | `pyfinbot-stock-delete` | AJAX modal |
| `/pyfinbot/stocks/sync/<market>/` | `pyfinbot-market-sync-action` | POST action |
| `/pyfinbot/transaction/list/` | `pyfinbot-transaction-list` | |
| `/pyfinbot/transaction/form/` | `pyfinbot-transaction-form` | create |
| `/pyfinbot/transaction/form/<record_id>/` | `pyfinbot-transaction-form` | update |
| `/pyfinbot/transaction/delete/<record_id>/` | `pyfinbot-transaction-delete` | AJAX modal |
| `/admin/` | — | Django admin |
| `/accounts/…` | — | allauth (login, signup, social, email) |

See `docs/url-map.md` for full annotated listing.

## Environment Variables

**Required (startup will fail or error without these):**
```
SECRET_KEY
DATABASE_ENGINE    # e.g. django.db.backends.postgresql
DATABASE_NAME
DATABASE_USER
DATABASE_PASSWORD
DATABASE_HOST      # e.g. db (Docker) or localhost
DATABASE_PORT      # e.g. 5432
```

**Key optional (with defaults):**
```
DJANGO_DEBUG              # default: 1 (True)
ALLOWED_HOSTS             # default: 127.0.0.1,localhost (comma-separated)
SITE_DOMAIN               # default: green-tech-hub.com
SITE_NAME                 # default: GreenTechHub
ENVIRONMENT               # default: production (enables proxy SSL headers)
EMAIL_BACKEND             # default: console backend
MICROSERVICE_TIMEOUT      # default: 10 (seconds)
```

**Superuser bootstrap (all three required together):**
```
DJANGO_SUPERUSER_USERNAME  (or SUPERUSER_USERNAME)
DJANGO_SUPERUSER_EMAIL     (or SUPERUSER_EMAIL)
DJANGO_SUPERUSER_PASSWORD  (or SUPERUSER_PASSWORD)
```

See `docs/environment.md` for complete list including OAuth and SMTP settings.

## Common Commands

```bash
# Development
python server.py runserver
python server.py migrate
python server.py makemigrations <addon_name>
python server.py createsuperuser
python server.py collectstatic

# Docker
docker compose up --build -d
docker compose exec greentechhub python server.py migrate --noinput
docker compose exec greentechhub python server.py collectstatic --noinput
docker compose logs -f greentechhub

# Tests (CI uses PostgreSQL; tests run on non-main branches)
python server.py test
```

## Key Gotchas

1. **`server.py` is manage.py.** Running `python manage.py ...` will fail. Always use `python server.py`.

2. **App label is `addons.<dirname>`.** Affects `AUTH_USER_MODEL`, cross-app ForeignKeys in migrations, and `apps.get_model("addons_authentication", "User")` calls.

3. **`context_processors.py` function must be `default_context(request)`.** Any other function name is silently ignored by the auto-discovery loop.

4. **Microservice must be registered in the DB.** `MicroserviceClient.forPrefix()` does a DB lookup at runtime. Go to `/admin/microservice/microservice/add/` and ensure `is_active=True`.

5. **`user.hasGroups()` includes role-inherited groups.** Raw `user.groups.filter(...)` only checks direct membership. Always use `hasGroups("code_name")` for access checks. For AND/OR/NOT logic use `G`, `AND`, `OR`, `NOT` from `addons.authentication.access`: `user.hasGroups(G("admin") & ~G("suspended"))`.

6. **URL kwarg is `record_id`, not `pk`.** `BaseMicroserviceFormView` reads `self.kwargs.get("record_id")`. Using `pk` in URL patterns causes edit views to behave like create.

7. **`profile.avatar.url` raises `ValueError`.** The avatar uses private storage with `base_url=None`. Use `profile.effective_avatar_url` or the `/me/avatar/` view instead.

8. **`transform_payload()` must strip read-only fields.** Microservice APIs reject or ignore calculated fields; `BaseMicroserviceFormView` sends all `cleaned_data` unless a `transform_payload()` override removes them.

9. **`Site` table is auto-configured post_migrate.** `base.signals.configure_site_after_migrate` updates the `django.contrib.sites` row from `SITE_DOMAIN`/`SITE_NAME`. Wrong env vars break allauth OAuth redirect URIs.

10. **Bootstrap classes are globally injected.** `base.apps.AppConfig.ready()` monkey-patches all Django form widgets to add `form-control`, `form-select`, `form-check-input`. Opt out on a widget with `attrs={"bs_skip": True}` or `widget.bs_skip = True`.
