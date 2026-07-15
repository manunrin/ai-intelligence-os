#!/usr/bin/env bash
set -euo pipefail

# AI Intelligence OS — Start Development Environment
# Usage: ./scripts/start.sh [up|rebuild]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

cd "$PROJECT_ROOT"

ACTION="${1:-up}"

case "$ACTION" in
  rebuild)
    echo "==> Building and starting all services (no cache)..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    docker compose -f "$COMPOSE_FILE" up -d
    ;;
  up|*)
    echo "==> Starting all services..."
    if [ ! -f .env ]; then
      echo "  Warning: .env not found. Copying from .env.example..."
      cp .env.example .env
    fi
    docker compose -f "$COMPOSE_FILE" up -d --build
    ;;
esac

echo ""
echo "==> Waiting for services to become healthy..."
sleep 5

docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "==> Services started."
echo "    Frontend: http://localhost:3000"
echo "    Backend:  http://localhost:8000/api/docs"
echo "    MinIO:    http://localhost:9001"
