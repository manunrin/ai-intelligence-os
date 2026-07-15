#!/usr/bin/env bash
set -euo pipefail

# AI Intelligence OS — Stop Development Environment
# Usage: ./scripts/stop.sh [--down]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

cd "$PROJECT_ROOT"

if [[ "${1:-}" == "--down" ]]; then
  echo "==> Stopping and removing all containers..."
  docker compose -f "$COMPOSE_FILE" down
elif [[ "${1:-}" == "--down-volumes" ]]; then
  echo "==> Stopping, removing containers AND deleting all data volumes..."
  echo "  WARNING: This action is irreversible!"
  docker compose -f "$COMPOSE_FILE" down -v
else
  echo "==> Stopping all services (data preserved)..."
  docker compose -f "$COMPOSE_FILE" stop
fi

echo "==> Done."
