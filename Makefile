SHELL := /bin/bash

APP_NAME := ai-intelligence-os
VERSION := $(shell cat VERSION)
COMPOSE := docker compose -f docker-compose.yml
ENV ?= development

.PHONY: start stop logs build test clean help \
        start-db stop-db rebuild init-db

# ── Lifecycle ──────────────────────────────────────────────

start:          ## Start all services (development)
	$(MAKE) _set_env && $(COMPOSE) up -d --build
	@echo "==> Waiting for services to become healthy..."
	@sleep 5
	@$(COMPOSE) ps

stop:           ## Stop all services (data preserved)
	$(COMPOSE) stop

rebuild:        ## Rebuild containers without cache
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

clean:          ## Remove containers, networks, and volumes
	$(COMPOSE) down -v
	@echo "==> All containers and volumes removed."

init-db:        ## Run database migrations
	$(COMPOSE) exec backend alembic upgrade head

# ── Observability ──────────────────────────────────────────

logs:           ## Follow all service logs
	$(COMPOSE) logs -f --tail=100

logs-svc:       ## Follow a single service log
	@if [ -z "$(svc)" ]; then echo "Usage: make logs-svc svc=<name>"; exit 1; fi
	$(COMPOSE) logs -f $(svc)

ps:             ## Show service status
	$(COMPOSE) ps

# ── Testing ────────────────────────────────────────────────

test:           ## Run backend tests
	$(COMPOSE) exec backend pytest

test-frontend:  ## Run frontend tests
	cd frontend && npm test

test-unit:      ## Run backend unit tests only
	$(COMPOSE) exec backend pytest tests/unit/ -v

test-integration: ## Run backend integration tests
	$(COMPOSE) exec backend pytest tests/integration/ -v

test-coverage:  ## Run backend tests with coverage report
	$(COMPOSE) exec backend pytest --cov=backend --cov-report=term-missing --cov-fail-under=60

# ── Development ────────────────────────────────────────────

shell:          ## Open backend shell
	$(COMPOSE) exec backend bash

db-shell:       ## Open PostgreSQL shell
	$(COMPOSE) exec postgres psql -U postgres -d ai_intelligence_os

redis-cli:      ## Open Redis CLI
	$(COMPOSE) exec redis redis-cli

# ── Internal ───────────────────────────────────────────────

_set_env:
	@if [ ! -f .env ]; then \
		cp .env.$(ENV).example .env; \
		echo "==> Created .env from .env.$(ENV).example"; \
	else \
		echo "==> .env already exists, skipping."; \
	fi

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
