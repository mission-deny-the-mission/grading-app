.PHONY: help build up down logs clean dev-build dev-up dev-down dev-logs test test-sequential test-verbose test-coverage test-failed test-fast lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build production Docker images"
	@echo "  up        - Start production services"
	@echo "  down      - Stop production services"
	@echo "  logs      - Show production service logs"
	@echo "  clean     - Remove all containers and volumes"
	@echo ""
	@echo "Development commands:"
	@echo "  dev-build - Build development Docker images"
	@echo "  dev-up    - Start development services"
	@echo "  dev-down  - Stop development services"
	@echo "  dev-logs  - Show development service logs"
	@echo "  dev-web   - Start Flask web service (port 5001)"
	@echo "  dev-worker- Start Celery worker"
	@echo "  dev-beat  - Start Celery beat"
	@echo ""
	@echo "Code quality:"
	@echo "  test            - Run tests in parallel (default, fast)"
	@echo "  test-sequential - Run tests sequentially (no parallelization)"
	@echo "  test-verbose    - Run tests with verbose output"
	@echo "  test-coverage   - Run tests with coverage report"
	@echo "  test-failed     - Re-run only previously failed tests"
	@echo "  test-fast       - Run tests with minimal output"
	@echo "  lint            - Run linting"
	@echo "  format          - Format code"
	@echo "  validate        - Validate bulk upload model loading fix"
	@echo "  validate-tests  - Run comprehensive bulk upload tests"

# Production commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Development commands
dev-build:
	docker compose -f docker-compose.dev.yml build

dev-up:
	docker compose -f docker-compose.dev.yml up -d

dev-down:
	docker compose -f docker-compose.dev.yml down

dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

# Start web service for development
dev-web:
	docker compose -f docker-compose.dev.yml --profile web up -d

# Start worker and beat services for development
dev-worker:
	docker compose -f docker-compose.dev.yml --profile worker up -d

dev-beat:
	docker compose -f docker-compose.dev.yml --profile beat up -d

# Code quality commands
test:
	@echo "Running tests in parallel with pytest-xdist..."
	docker compose -f docker-compose.dev.yml exec app pytest

test-sequential:
	@echo "Running tests sequentially (no parallelization)..."
	docker compose -f docker-compose.dev.yml exec app pytest -n 0

test-verbose:
	@echo "Running tests with verbose output..."
	docker compose -f docker-compose.dev.yml exec app pytest -vv

test-coverage:
	@echo "Running tests with coverage (sequential)..."
	docker compose -f docker-compose.dev.yml exec app pytest -n 0 --cov=app --cov=models --cov=tasks --cov=desktop --cov-report=html --cov-report=term-missing

test-failed:
	@echo "Re-running only failed tests..."
	docker compose -f docker-compose.dev.yml exec app pytest --lf

test-fast:
	@echo "Running tests with minimal output..."
	docker compose -f docker-compose.dev.yml exec app pytest -q

lint:
	docker compose -f docker-compose.dev.yml exec app flake8 .
	docker compose -f docker-compose.dev.yml exec app pylint *.py

format:
	docker compose -f docker-compose.dev.yml exec app black .
	docker compose -f docker-compose.dev.yml exec app isort .

# Validation commands
validate:
	python validate_bulk_upload_fix.py

validate-tests:
	cd tests && python simple_test_runner.py

# Database commands
init-db:
	docker compose -f docker-compose.dev.yml exec app flask init-db

# Shell access
shell:
	docker compose -f docker-compose.dev.yml exec app bash

# Quick start for development
dev: dev-build dev-up
	@echo "Development environment started!"
	@echo "To start the Flask web app: make dev-web"
	@echo "Flask app will be available at: http://localhost:5001"
	@echo "Flower (Celery monitor): http://localhost:5555"
	@echo "Redis: localhost:6379"
	@echo ""
	@echo "To start worker: make dev-worker"
	@echo "To start beat: make dev-beat"
	@echo "To access shell: make shell"
