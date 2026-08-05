.PHONY: up down test test-unit lint format

up: ## sobe tudo (Postgres + migrations + seed + API) sem passos manuais
	docker compose up --build

down:
	docker compose down

test: ## suite completa (requer Postgres: docker compose up -d db)
	docker compose up -d db
	uv run pytest

test-unit: ## apenas testes unitarios (sem banco, sem rede)
	uv run pytest -m "not integration"

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .
