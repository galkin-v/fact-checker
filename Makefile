.PHONY: install check test lint format run compose-up compose-down

install:
	uv sync --frozen

check: lint test

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

format:
	uv run ruff check --fix .
	uv run ruff format .

run:
	uv run uvicorn fact_checker.api:app --reload --port 8080

compose-up:
	docker compose up --build

compose-down:
	docker compose down

