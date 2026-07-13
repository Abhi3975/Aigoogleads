# ===========================================================================
# AI Ads Agent — developer task runner
# ===========================================================================
.DEFAULT_GOAL := help
SHELL := /bin/bash

BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Environment ----------------------------------------------------------
.PHONY: env
env: ## Create .env files from examples if missing
	@[ -f .env ] || cp .env.example .env
	@[ -f $(BACKEND_DIR)/.env ] || cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env
	@[ -f $(FRONTEND_DIR)/.env.local ] || cp $(FRONTEND_DIR)/.env.example $(FRONTEND_DIR)/.env.local
	@echo "Environment files ready."

# --- Backend --------------------------------------------------------------
.PHONY: backend-install
backend-install: ## Install backend dependencies with uv
	cd $(BACKEND_DIR) && uv sync --all-extras

.PHONY: backend-run
backend-run: ## Run FastAPI dev server
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: backend-lint
backend-lint: ## Lint + type-check backend
	cd $(BACKEND_DIR) && uv run ruff check . && uv run mypy app

.PHONY: backend-format
backend-format: ## Format backend code
	cd $(BACKEND_DIR) && uv run ruff format . && uv run ruff check --fix .

.PHONY: backend-test
backend-test: ## Run backend tests
	cd $(BACKEND_DIR) && uv run pytest

# --- Frontend -------------------------------------------------------------
.PHONY: frontend-install
frontend-install: ## Install frontend dependencies with pnpm
	cd $(FRONTEND_DIR) && pnpm install

.PHONY: frontend-run
frontend-run: ## Run Next.js dev server
	cd $(FRONTEND_DIR) && pnpm dev

.PHONY: frontend-lint
frontend-lint: ## Lint frontend
	cd $(FRONTEND_DIR) && pnpm lint

.PHONY: frontend-format
frontend-format: ## Format frontend code
	cd $(FRONTEND_DIR) && pnpm format

# --- Docker ---------------------------------------------------------------
.PHONY: up
up: ## Start full stack via docker compose
	docker compose up -d --build

.PHONY: down
down: ## Stop stack
	docker compose down

.PHONY: logs
logs: ## Tail all service logs
	docker compose logs -f

.PHONY: ps
ps: ## Show running services
	docker compose ps

# --- Quality --------------------------------------------------------------
.PHONY: lint
lint: backend-lint frontend-lint ## Lint everything

.PHONY: format
format: backend-format frontend-format ## Format everything

.PHONY: test
test: backend-test ## Run all tests
