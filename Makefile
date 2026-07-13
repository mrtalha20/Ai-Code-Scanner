.PHONY: dev stop build migrate migrate-down migrate-create test test-backend test-frontend \
        lint lint-backend lint-frontend format clean logs shell-backend shell-frontend \
        db-shell redis-cli setup help

# ── Colours ───────────────────────────────────────────────────
CYAN  := \033[0;36m
GREEN := \033[0;32m
RESET := \033[0m

# ── Default target ────────────────────────────────────────────
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "$(CYAN)AI Code Security Scanner$(RESET)"
	@echo "────────────────────────────────────────"
	@echo "$(GREEN)make setup$(RESET)              First-time setup (copy .env, install deps)"
	@echo "$(GREEN)make dev$(RESET)                Start all services in development mode"
	@echo "$(GREEN)make stop$(RESET)               Stop all services"
	@echo "$(GREEN)make build$(RESET)              Rebuild all Docker images"
	@echo "$(GREEN)make migrate$(RESET)            Run Alembic migrations (upgrade head)"
	@echo "$(GREEN)make migrate-down$(RESET)       Rollback last migration"
	@echo "$(GREEN)make migrate-create msg=...$(RESET)  Create a new migration"
	@echo "$(GREEN)make test$(RESET)               Run all tests"
	@echo "$(GREEN)make test-backend$(RESET)       Run backend tests with coverage"
	@echo "$(GREEN)make test-frontend$(RESET)      Run frontend tests"
	@echo "$(GREEN)make lint$(RESET)               Lint all code"
	@echo "$(GREEN)make format$(RESET)             Auto-format all code"
	@echo "$(GREEN)make logs$(RESET)               Tail logs for all services"
	@echo "$(GREEN)make shell-backend$(RESET)      Open shell in backend container"
	@echo "$(GREEN)make shell-frontend$(RESET)     Open shell in frontend container"
	@echo "$(GREEN)make db-shell$(RESET)           Open psql in postgres container"
	@echo "$(GREEN)make redis-cli$(RESET)          Open redis-cli in redis container"
	@echo "$(GREEN)make clean$(RESET)              Remove containers, volumes, cache"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────
setup:
	@echo "$(CYAN)Setting up project...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN).env created from .env.example — fill in your secrets!$(RESET)"; \
	else \
		echo ".env already exists, skipping."; \
	fi
	@echo "$(CYAN)Installing frontend dependencies...$(RESET)"
	@cd frontend && npm install
	@echo "$(CYAN)Installing backend dependencies...$(RESET)"
	@cd backend && pip install -r requirements-dev.txt
	@echo "$(GREEN)Setup complete. Run 'make dev' to start.$(RESET)"

# ── Docker lifecycle ─────────────────────────────────────────
dev:
	@echo "$(CYAN)Starting development environment...$(RESET)"
	docker compose up --build

dev-detached:
	docker compose up --build -d
	@echo "$(GREEN)Services running in background. Use 'make logs' to tail.$(RESET)"

stop:
	docker compose down

build:
	docker compose build --no-cache

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build

# ── Database migrations ───────────────────────────────────────
migrate:
	@echo "$(CYAN)Running migrations...$(RESET)"
	docker compose exec backend alembic upgrade head

migrate-down:
	@echo "$(CYAN)Rolling back last migration...$(RESET)"
	docker compose exec backend alembic downgrade -1

migrate-create:
	@if [ -z "$(msg)" ]; then echo "Usage: make migrate-create msg='your message'"; exit 1; fi
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

migrate-history:
	docker compose exec backend alembic history --verbose

# ── Testing ───────────────────────────────────────────────────
test: test-backend test-frontend

test-backend:
	@echo "$(CYAN)Running backend tests...$(RESET)"
	docker compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80

test-frontend:
	@echo "$(CYAN)Running frontend tests...$(RESET)"
	docker compose exec frontend npm run test -- --passWithNoTests

test-integration:
	@echo "$(CYAN)Running integration tests...$(RESET)"
	docker compose exec backend pytest tests/integration/ -v

# ── Linting & formatting ──────────────────────────────────────
lint: lint-backend lint-frontend

lint-backend:
	@echo "$(CYAN)Linting backend...$(RESET)"
	docker compose exec backend ruff check app/ tests/
	docker compose exec backend mypy app/

lint-frontend:
	@echo "$(CYAN)Linting frontend...$(RESET)"
	docker compose exec frontend npm run lint

format:
	@echo "$(CYAN)Formatting backend...$(RESET)"
	docker compose exec backend ruff format app/ tests/
	docker compose exec backend ruff check --fix app/ tests/
	@echo "$(CYAN)Formatting frontend...$(RESET)"
	docker compose exec frontend npm run format

# ── Logs & shells ─────────────────────────────────────────────
logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

shell-backend:
	docker compose exec backend /bin/bash

shell-frontend:
	docker compose exec frontend /bin/sh

db-shell:
	docker compose exec postgres psql -U scanner -d scanner_db

redis-cli:
	docker compose exec redis redis-cli

# ── Cleanup ───────────────────────────────────────────────────
clean:
	@echo "$(CYAN)Cleaning up...$(RESET)"
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/.next frontend/node_modules/.cache
	@echo "$(GREEN)Clean complete.$(RESET)"

# ── Monitoring ────────────────────────────────────────────────
monitoring:
	@echo "$(CYAN)Starting monitoring stack (Prometheus + Grafana)...$(RESET)"
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d prometheus grafana
	@echo "$(GREEN)Prometheus: http://localhost:9090$(RESET)"
	@echo "$(GREEN)Grafana:    http://localhost:3001  (admin / admin)$(RESET)"

monitoring-stop:
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml stop prometheus grafana

# ── K8s deploy helpers ────────────────────────────────────────
k8s-apply:
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/postgres/statefulset.yaml
	kubectl apply -f k8s/redis/deployment.yaml
	kubectl apply -f k8s/backend/deployment.yaml
	kubectl apply -f k8s/frontend/deployment.yaml
	kubectl apply -f k8s/ingress.yaml

k8s-status:
	kubectl get pods,services,ingress -l app=scanner-backend
	kubectl get pods,services -l app=scanner-frontend

k8s-migrate:
	$(eval POD := $(shell kubectl get pod -l app=scanner-backend -o jsonpath="{.items[0].metadata.name}"))
	kubectl exec $(POD) -- alembic upgrade head
