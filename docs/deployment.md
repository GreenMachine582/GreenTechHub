# Deployment

## Architecture Overview

```
Internet
    │  HTTPS
    ▼
Cloudflare Tunnel (public domain: green-tech-hub.com)
    │  HTTP
    ▼
Homelab Server
    │
    ├── greentechhub container (Gunicorn, port 8000)
    │       │  SQL
    │       ▼
    └── db container (PostgreSQL 16, port 5432)
```

- Django serves via **Gunicorn** (no nginx in the stack — Cloudflare Tunnel connects directly to port 8000)
- Static files served by **WhiteNoise** (compressed in production, no separate static server needed)
- Private media (`private_media/`) served by Django's `serve_my_avatar` view
- PostgreSQL runs in a sibling container; host port `5431` maps to container `5432`

---

## Docker Stack

**`docker-compose.yml` services:**

### `db` service

| Property | Value |
|---|---|
| Image | `postgres:16` |
| Container name | `greentechhub_db` |
| Host port | `5431` → container `5432` |
| Volume | `greentechhub_postgres_data:/var/lib/postgresql/data` (named, persistent) |
| Env file | `.env` (expects `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) |

### `greentechhub` service

| Property | Value |
|---|---|
| Build | `Dockerfile` in repo root |
| Container name | `greentechhub` |
| Host port | `8000` → container `8000` |
| Depends on | `db` |
| Restart | `unless-stopped` |
| Env file | `.env` |
| Volumes | `./staticfiles:/app/staticfiles`, `./media:/app/media`, `./private_media:/app/private_media` |

Volumes are **bind mounts** — directories on the host are shared with the container. This means `staticfiles/`, `media/`, and `private_media/` persist across container rebuilds and image updates.

### Network

`greentechhub_network` (bridge) — both containers share this network. The app connects to the DB via hostname `db` (the service name).

---

## Gunicorn Entry Point

**`Dockerfile` CMD:**
```dockerfile
CMD ["gunicorn", "server.wsgi:application", "--bind", "0.0.0.0:8000"]
```

The WSGI application is at `server.wsgi:application` (the Django project package is named `server/`, so the module path is `server.wsgi`). This is a common confusion point — do not use `wsgi:application`.

**Dockerfile base:** `python:3.14-slim`

System dependencies installed:
- `build-essential` — for compiling Python packages
- `libpq-dev` — for psycopg2 (PostgreSQL adapter)
- `libjpeg-dev`, `zlib1g-dev` — for Pillow (image processing)

---

## Static Files in Production

When `DJANGO_DEBUG=0`:
- `STATIC_ROOT = BASE_DIR / "staticfiles"` (set only in non-debug mode)
- Static storage: `whitenoise.storage.CompressedStaticFilesStorage` (gzip + brotli compression, cache-busted filenames)
- WhiteNoise middleware serves static files directly from `staticfiles/` — no nginx required

**Must run after every deploy:**
```bash
python server.py collectstatic --noinput
```
This copies all addon `static/` directories into `staticfiles/`. The `staticfiles/` bind mount makes the output available on the host and persists across rebuilds.

In development (`DJANGO_DEBUG=1`): `StaticFilesStorage` is used (no compression); `collectstatic` is not needed as files are served directly.

---

## Private Media

`PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"` stores uploaded user avatars.

- No direct URL — `base_url=None` on the storage backend
- Access only via `/me/avatar/` → `serve_my_avatar` view (enforces authentication, sets cache headers)
- Bind-mounted to host `./private_media` — persists across rebuilds

---

## Initial Setup (First Deploy)

```bash
# Create required directories (setup.sh does this automatically)
mkdir -p staticfiles media private_media

# Start containers
docker compose up --build -d

# Run migrations
docker compose exec greentechhub python server.py migrate --noinput

# Collect static files
docker compose exec greentechhub python server.py collectstatic --noinput
```

The superuser is created automatically on `migrate` if `DJANGO_SUPERUSER_*` env vars are set (see `docs/environment.md`).

---

## CI/CD Pipeline

### Testing (non-main branches)

**File:** `.github/workflows/django_tests.yml`

**Trigger:** Push to any branch except `main`

**Steps:**
1. Checkout repository
2. Set up Python 3.12
3. Install `pip` + `requirements.txt`
4. Run `python server.py migrate`
5. Run `python server.py test`

**Test database:** A PostgreSQL 15 service is spun up in the Actions runner. Test database name comes from `DATABASE_NAME` env var set in the workflow (typically `greentechhub_test`).

### Production Deployment (main branch)

**File:** `.github/workflows/server_deployment.yml`

**Trigger:** Push to `main`

**Concurrency:** Single deployment at a time (concurrent runs are cancelled)

**Steps:**
1. Checkout repository
2. Install `cloudflared` CLI
3. Write SSH private key from `SERVER_PRIVATE_KEY` secret
4. Configure SSH to use Cloudflare Access tunnel:
   ```
   ProxyCommand cloudflared access ssh --hostname $SERVER_HOST
   ```
   with `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` as service token credentials
5. Test SSH connectivity
6. SSH to homelab and run:
   ```bash
   sudo /root/homelab/scripts/deploy_project.sh python_projects/greentechhub GreenTechHub main
   ```

The `deploy_project.sh` script lives on the homelab server (not in this repo). It receives the project directory, project name, and branch as arguments. It typically calls the project's `setup.sh`.

---

## setup.sh Walkthrough

`setup.sh` is the project-level deploy script. It's called by the homelab's generic deploy script.

**What it does (in order):**

1. **Validate prerequisites** — checks that `git` and `docker compose` (v2) or `docker-compose` (v1) are available
2. **Create required directories** — `mkdir -p staticfiles media private_media`
3. **Git update** — `git fetch origin && git reset --hard origin/<branch>`
4. **Docker build** — `docker compose pull` (optional base image update) + `docker compose build`
5. **Start containers** — `docker compose up -d --remove-orphans`
6. **Run migrations** — `docker compose exec greentechhub python server.py migrate --noinput`
7. **Collect static** — `docker compose exec greentechhub python server.py collectstatic --noinput`
8. **Status check** — shows container status after deploy

Supports both Docker Compose v1 (`docker-compose`) and v2 (`docker compose`) via detection logic.

Error handling: uses `set -e` and a trap that reports the failed step.

---

## Rollback

No automated rollback. Manual process:

```bash
# SSH to homelab
ssh user@homelab

# Find last good commit
cd /path/to/python_projects/greentechhub
git log --oneline -10

# Roll back
git reset --hard <commit-hash>

# Re-deploy (runs migrations + static collect)
bash setup.sh
```

**Note:** Rolling back may not roll back database migrations. If the new code added migrations, rolling back the code without rolling back migrations can cause issues. In that case, run:
```bash
docker compose exec greentechhub python server.py migrate <app_name> <previous_migration_number>
```
before resetting the code.

---

## Accessing Logs

```bash
# App container logs
docker compose logs -f greentechhub

# Database logs
docker compose logs -f db

# All containers
docker compose logs -f

# Since last N minutes
docker compose logs --since 30m greentechhub
```

Django logging is configured in `server/logging_config.py`. Default level: INFO to console.

---

## Useful Docker Commands

```bash
# Start all services
docker compose up -d

# Rebuild and restart app only
docker compose up -d --build greentechhub

# Stop all services
docker compose down

# Stop and remove volumes (WARNING: destroys database)
docker compose down -v

# Open a shell in the app container
docker compose exec greentechhub bash

# Run any Django management command
docker compose exec greentechhub python server.py <command>

# Check container status
docker compose ps
```
