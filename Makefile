.PHONY: help up down build-backend build-frontend logs psql test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker Compose ──────────────────────────────────────────────────────

up: ## Start all services (detached)
	docker compose -f infra/docker-compose.yml --env-file infra/.env up -d

down: ## Stop and remove all containers
	docker compose -f infra/docker-compose.yml down

build-backend: ## Rebuild the backend image
	docker compose -f infra/docker-compose.yml build backend

build-frontend: ## Rebuild the frontend image
	docker compose -f infra/docker-compose.yml build frontend

logs: ## Tail logs from all services
	docker compose -f infra/docker-compose.yml logs -f

psql: ## Connect to the database via psql
	docker exec -it rag-postgres psql -U rag_user -d rag_platform

# ── Python / Backend ────────────────────────────────────────────────────

backend-install: ## Install backend dev dependencies
	cd backend && pip install -r requirements.txt && pip install ruff black mypy pytest pytest-asyncio httpx

backend-lint: ## Lint backend code with ruff
	cd backend && ruff check .

backend-format: ## Format backend code with black
	cd backend && black .

backend-typecheck: ## Type-check backend with mypy
	cd backend && mypy app tests

backend-test: ## Run backend tests
	cd backend && pytest -v --cov=app --cov-report=term-missing

# ── Frontend ────────────────────────────────────────────────────────────

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-dev: ## Start frontend dev server
	cd frontend && npm run dev

frontend-lint: ## Lint frontend
	cd frontend && npm run lint

frontend-typecheck: ## Type-check frontend
	cd frontend && npx tsc --noEmit

frontend-build: ## Build frontend for production
	cd frontend && npm run build

# ── Other ───────────────────────────────────────────────────────────────

test: backend-test ## Run all tests (backend for now)
