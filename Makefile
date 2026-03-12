.PHONY: install test lint format typecheck security build all

install:
	uv sync --all-groups
test:
	uv run pytest
lint:
	uv run ruff check src/ tests/
format:
	uv run ruff format src/ tests/
typecheck:
	uv run mypy src/
security:
	uv run bandit -r src/ -ll
build:
	sudo docker build -t budget_automation:latest .
all: format lint typecheck security test
