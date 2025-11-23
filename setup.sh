#!/usr/bin/env bash
set -Eeuo pipefail

###################################
# Helper functions & error trap   #
###################################

INFO()  { echo -e "ℹ️  $*"; }
OK()    { echo -e "✅ $*"; }
WARN()  { echo -e "⚠️  $*" >&2; }
ERR()   { echo -e "❌ $*" >&2; }

on_error() {
  ERR "Deployment failed on line $1. Check the logs above for details."
}
trap 'on_error $LINENO' ERR

###################################
# Configuration                   #
###################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

GIT_BRANCH="${GIT_BRANCH:-main}"

DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-$PROJECT_ROOT/docker-compose.yml}"

###################################
# Start                           #
###################################

echo "🚀 Starting greentechhub Docker deployment as $(whoami)..."

INFO "Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

###################################
# Sanity checks                   #
###################################

if ! command -v git >/dev/null 2>&1; then
  ERR "git is not installed or not in PATH."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  ERR "docker is not installed or not in PATH."
  exit 1
fi

# Prefer 'docker compose' (v2), fall back to 'docker-compose' if needed
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
    WARN "'docker compose' not found, falling back to 'docker-compose'."
  else
    ERR "Neither 'docker compose' nor 'docker-compose' is available."
    exit 1
  fi
fi

if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
  ERR "docker-compose.yml not found at $DOCKER_COMPOSE_FILE"
  exit 1
fi

###################################
# Prepare static & media dirs     #
###################################

INFO "Ensuring staticfiles and media directories exist..."
mkdir -p "$PROJECT_ROOT/staticfiles" "$PROJECT_ROOT/media"
OK "Static and media directories ready."

###################################
# Pull latest code                #
###################################

INFO "Fetching latest code from Git (branch: $GIT_BRANCH)..."
git fetch origin "$GIT_BRANCH"
git reset --hard "origin/$GIT_BRANCH"
OK "Code updated from origin/$GIT_BRANCH"

###################################
# Build & update Docker stack     #
###################################

INFO "Pulling latest base images (if any)..."
$DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" pull || WARN "Image pull step failed or not needed."

INFO "Building greentechhub image..."
$DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" build

INFO "Bringing up containers..."
$DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" up -d --remove-orphans

###################################
# Django collectstatic            #
###################################

INFO "Collecting static files inside greentechhub container..."
if $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" exec -T greentechhub python server.py collectstatic --noinput; then
  OK "Static files collected successfully."
else
  WARN "collectstatic failed. Check the greentechhub container logs."
fi

###################################
# Post-deploy info                #
###################################

OK "Docker deployment complete."

INFO "Current container status:"
$DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" ps

cat <<EOF

📌 Quick reference:
  - App URL (host):  http://<server-ip>:8000
  - DB exposed port: 5431 (mapped to container's 5432)
  - Network:         greentechhub_network
  - To see logs:     $DOCKER_COMPOSE_CMD logs -f greentechhub

EOF
