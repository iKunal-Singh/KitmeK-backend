.PHONY: up down logs build migrate seed test lint format typecheck shell health

# Docker operations
up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f api

build:
	docker-compose build

# Database operations
migrate:
	docker-compose exec api alembic upgrade head

seed:
	docker-compose exec api python -m src.scripts.seed

# Testing
test:
	docker-compose exec api pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Code quality
lint:
	docker-compose exec api flake8 src/ tests/

format:
	docker-compose exec api black src/ tests/

typecheck:
	docker-compose exec api mypy src/

# Utilities
shell:
	docker-compose exec api bash

health:
	curl -s http://localhost:8000/health | python3 -m json.tool
