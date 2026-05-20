.PHONY: help build up down logs test lint format clean migrate

help:
	@echo "Drone Livestock Monitoring Backend - Make Commands"
	@echo "=================================================="
	@echo "make build          - Build Docker images"
	@echo "make up              - Start all services (development)"
	@echo "make up-prod         - Start all services (production)"
	@echo "make down            - Stop all services"
	@echo "make logs            - Follow API logs"
	@echo "make logs-all        - Follow all service logs"
	@echo "make test            - Run tests"
	@echo "make lint            - Run linter"
	@echo "make format          - Format code"
	@echo "make clean           - Clean up Docker volumes"
	@echo "make migrate         - Run database migrations"
	@echo "make shell           - Open Python shell"
	@echo "make status          - Show service status"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "✅ Services started"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "PgAdmin: http://localhost:5050"
	@echo "MinIO: http://localhost:9001"
	@echo "Grafana: http://localhost:3000"

up-prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production services started"

down:
	docker-compose down
	@echo "✅ Services stopped"

down-prod:
	docker-compose -f docker-compose.prod.yml down
	@echo "✅ Production services stopped"

logs:
	docker-compose logs -f api

logs-all:
	docker-compose logs -f

test:
	pytest -v

lint:
	flake8 app config tests
	mypy app

format:
	black app config tests
	isort app config tests

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

migrate:
	docker-compose exec api alembic upgrade head

shell:
	docker-compose exec api python

status:
	docker-compose ps

# Development shortcuts
dev-install:
	pip install -r requirements.txt

dev-run:
	python app/main.py

db-init:
	alembic init -t async

db-revision:
	alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

# Docker shortcuts
docker-build:
	docker build -t drone-livestock:latest -f docker/Dockerfile .

docker-run:
	docker run -p 8000:8000 -e DATABASE_URL=... drone-livestock:latest

# Check service health
health:
	@echo "Checking services..."
	@curl -s http://localhost:8000/health/all | python -m json.tool
	@echo ""

.DEFAULT_GOAL := help
