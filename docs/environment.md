# Environment Variables

All variables are loaded from a `.env` file at startup via `python-dotenv`. The `.env` file is **not committed** (blocked by `.gitignore`). You must create it manually.

`load_dotenv()` is called at module import time in `server/settings.py`. Variables can also be set as real OS environment variables — dotenv does not override existing env vars by default.

---

## Required Variables

The application will fail to start or error on first request without these:

| Variable | Example | Description |
|---|---|---|
| `SECRET_KEY` | `django-insecure-...` | Django cryptographic secret key |
| `DATABASE_ENGINE` | `django.db.backends.postgresql` | Django database backend path |
| `DATABASE_NAME` | `greentechhub` | Database name |
| `DATABASE_USER` | `postgres` | Database user |
| `DATABASE_PASSWORD` | `s3cr3t` | Database password |
| `DATABASE_HOST` | `db` or `localhost` | Database hostname (`db` in Docker; `localhost` for local dev) |
| `DATABASE_PORT` | `5432` | Database port |

---

## Django Settings Variables

| Variable | Default | Description |
|---|---|---|
| `DJANGO_DEBUG` | `1` | Debug mode. Any of `1`, `true`, `yes`, `on` enables it |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated list of allowed hostnames |
| `ENVIRONMENT` | `production` | If `production`, enables `USE_X_FORWARDED_HOST` and `SECURE_PROXY_SSL_HEADER` for reverse proxy support |
| `SITE_DOMAIN` | `green-tech-hub.com` | Used for `django.contrib.sites`, `CSRF_TRUSTED_ORIGINS`, and allauth email links |
| `SITE_NAME` | `GreenTechHub` | Used for email subjects and template display |
| `MICROSERVICE_TIMEOUT` | `10` | HTTP timeout in seconds for all microservice requests |

**Note on `ENVIRONMENT`:** When set to `production`, Django trusts `X-Forwarded-Proto` and `X-Forwarded-Host` headers from the reverse proxy. This is required when running behind Cloudflare Tunnel + nginx. In local development, do not set or set to `development` to avoid trusting these headers.

**Note on `SITE_DOMAIN`:** This value is written to the `django.contrib.sites.Site` row on every `post_migrate` by `base.signals.configure_site_after_migrate`. Allauth uses the Site record to build OAuth callback URLs and email confirmation links. If this is wrong, OAuth redirects and email links will point to the wrong domain.

---

## Email Settings

| Variable | Default | Description |
|---|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Use `django.core.mail.backends.smtp.EmailBackend` for production |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_USE_TLS` | `true` | Enable STARTTLS (for port 587) |
| `EMAIL_TIMEOUT` | `30` | SMTP connection timeout in seconds |
| `EMAIL_HOST_USER` | _(none)_ | SMTP username / sender address |
| `EMAIL_HOST_PASSWORD` | _(none)_ | SMTP password or app password |
| `DEFAULT_FROM_EMAIL` | same as `EMAIL_HOST_USER` | Default "From" address for outgoing email |
| `SERVER_EMAIL` | same as `DEFAULT_FROM_EMAIL` | Address for error emails to admins |

**Allauth uses email** for account confirmation and password reset. In development the console backend logs emails to stdout. In production set `EMAIL_BACKEND` to SMTP and configure credentials.

---

## OAuth / Social Auth

Both sets of credentials must be obtained from the respective developer consoles and registered as OAuth apps pointing to your domain.

| Variable | Description |
|---|---|
| `SOCIAL_AUTH_CLIENT_ID_GOOGLE` | Google OAuth2 client ID |
| `SOCIAL_AUTH_CLIENT_SECRET_GOOGLE` | Google OAuth2 client secret |
| `SOCIAL_AUTH_CLIENT_ID_GITHUB` | GitHub OAuth App client ID |
| `SOCIAL_AUTH_CLIENT_SECRET_GITHUB` | GitHub OAuth App client secret |

**Google OAuth callback URL:** `https://<SITE_DOMAIN>/accounts/google/login/callback/`
**GitHub OAuth callback URL:** `https://<SITE_DOMAIN>/accounts/github/login/callback/`

Social auth still works in development if these are left empty — the login buttons will be absent or error. Set `DJANGO_DEBUG=1` to suppress errors.

---

## Superuser Bootstrap

All three variables must be set together for the auto-creation to trigger. If any is missing, the bootstrap is skipped (logged at INFO level).

| Variable | Alias accepted |
|---|---|
| `DJANGO_SUPERUSER_USERNAME` | `SUPERUSER_USERNAME` |
| `DJANGO_SUPERUSER_EMAIL` | `SUPERUSER_EMAIL` |
| `DJANGO_SUPERUSER_PASSWORD` | `SUPERUSER_PASSWORD` |

This runs on every `post_migrate` and is idempotent. It creates the user if the username doesn't exist, or updates the existing user (ensuring `is_superuser`, `is_staff`, correct Role). Password is only set on **creation** — changing this env var does not change an existing user's password.

---

## GitHub Actions Secrets

These are not in `.env` — set them in GitHub repository → Settings → Secrets and variables → Actions.

| Secret | Description |
|---|---|
| `SERVER_PRIVATE_KEY` | SSH private key for connecting to homelab server |
| `SERVER_HOST` | Cloudflare Tunnel hostname for the homelab |
| `SERVER_USERNAME` | SSH username on homelab |
| `CF_ACCESS_CLIENT_ID` | Cloudflare Access service token client ID |
| `CF_ACCESS_CLIENT_SECRET` | Cloudflare Access service token client secret |

---

## Example `.env` File

```dotenv
# Django core
SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=1
ALLOWED_HOSTS=127.0.0.1,localhost
ENVIRONMENT=development

# Database (local dev)
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=greentechhub
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Site identity
SITE_DOMAIN=localhost:8000
SITE_NAME=GreenTechHub Dev

# Email (console in dev — no credentials needed)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Superuser auto-creation
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=ChangeMe123!

# OAuth (optional for local dev)
# SOCIAL_AUTH_CLIENT_ID_GOOGLE=...
# SOCIAL_AUTH_CLIENT_SECRET_GOOGLE=...
# SOCIAL_AUTH_CLIENT_ID_GITHUB=...
# SOCIAL_AUTH_CLIENT_SECRET_GITHUB=...
```

---

## Docker `compose` Environment

`docker-compose.yml` passes the `.env` file directly to both containers. The PostgreSQL `db` container uses `POSTGRES_*` variables — you may need to add these to your `.env` to match the `DATABASE_*` values:

```dotenv
# Add these to .env for docker-compose db service:
POSTGRES_DB=greentechhub
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```
