#!/usr/bin/env bash
set -euo pipefail

# AI Intelligence OS — View Development Environment Logs
# Usage: ./scripts/logs.sh [service] [-f]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

cd "$PROJECT_ROOT"

SERVICE="${1:-}"
FOLLOW=false

# Parse flags
for arg in "${@}"; do
  case "$arg" in
    -f|--follow) FOLLOW=true ;;
  esac
done

if [ -n "$SERVICE" ] && [ "$SERVICE" != "-f" ] && [ "$SERVICE" != "--follow" ]; then
  echo "==> Tailing logs for service: $SERVICE"
  if $FOLLOW; then
    docker compose -f "$COMPOSE_FILE" logs -f "$SERVICE"
  else
    docker compose -f "$COMPOSE_FILE" logs --tail=100 "$SERVICE"
  fi
else
  echo "==> Tailing logs for all services"
  if $FOLLOW; then
    docker compose -f "$COMPOSE_FILE" logs -f --tail=50
  else
    docker compose -f "$COMPOSE_FILE" logs --tail=50
  fi
fi
