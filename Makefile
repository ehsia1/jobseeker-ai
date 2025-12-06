.PHONY: help install dev-install test lint format type-check pre-commit clean docker-build docker-up docker-down docker-logs migrate seed

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  type-check   - Run type checking"
	@echo "  pre-commit   - Run pre-commit hooks"
	@echo "  clean        - Clean up build artifacts"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up    - Start Docker services"
	@echo "  docker-down  - Stop Docker services"
	@echo "  docker-logs  - Show Docker logs"
	@echo "  migrate      - Run database migrations"
	@echo "  seed         - Seed database with test data"

# Python environment
install:
	poetry install --no-dev

dev-install:
	poetry install
	poetry run pre-commit install

# Code quality
lint:
	poetry run ruff check backend/ tests/
	poetry run black --check backend/ tests/

format:
	poetry run black backend/ tests/
	poetry run ruff --fix backend/ tests/

type-check:
	poetry run mypy backend/

pre-commit:
	poetry run pre-commit run --all-files

# Testing
test:
	poetry run pytest tests/ -v --cov=backend --cov-report=html --cov-report=term-missing

test-unit:
	poetry run pytest tests/backend/unit/ -v -m unit

test-integration:
	poetry run pytest tests/backend/integration/ -v -m integration

test-e2e:
	poetry run pytest tests/frontend/e2e/ -v

test-chaos:
	@echo "Running chaos tests for free-tier limits..."
	poetry run pytest tests/backend/chaos/ -v -m chaos

test-redis-limits:
	@echo "Testing Redis 10K command limit..."
	poetry run pytest tests/backend/chaos/test_redis_exhaustion.py -v

test-db-limits:
	@echo "Testing database size limits..."
	poetry run pytest tests/backend/chaos/test_database_limits.py -v

test-smoke:
	@echo "Running smoke tests..."
	chmod +x tests/scripts/smoke_test.sh
	./tests/scripts/smoke_test.sh

test-coverage:
	poetry run pytest tests/ --cov=backend --cov-report=html --cov-report=term --cov-fail-under=70

# Docker operations
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v
	docker system prune -f

# Database operations
migrate:
	poetry run alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	poetry run alembic revision --autogenerate -m "$$msg"

seed:
	poetry run python scripts/seed_database.py

# Ingestion testing
test-ingestion:
	poetry run python scripts/test_ingestion.py

# Matching testing
test-matching:
	poetry run python scripts/test_matching.py

# Comprehensive system test
test-all:
	poetry run python scripts/test_all.py

# Development server
dev-server:
	poetry run uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8080

dev-worker:
	poetry run celery -A backend.workers.celery_app worker --loglevel=info --reload

dev-beat:
	poetry run celery -A backend.workers.celery_app beat --loglevel=info

# Monitoring
celery-monitor:
	poetry run celery -A backend.workers.celery_app flower

monitor-redis:
	@echo "Redis Usage:"
	@curl -s http://localhost:8000/health/cache-stats | python -m json.tool

monitor-db:
	@echo "Database Usage:"
	@curl -s http://localhost:8000/health/metrics | python -m json.tool | grep -A5 '"database"'

monitor-all:
	@echo "System Metrics:"
	@curl -s http://localhost:8000/health/metrics | python -m json.tool

# Cleanup
clean:
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf dist/ build/ htmlcov/

# Installation shortcuts
setup: dev-install docker-up migrate seed
	@echo "Development environment ready!"

teardown: docker-down docker-clean clean
	@echo "Environment cleaned up!"