test:
	uv run pytest
build:
	sudo docker build -t budget_automation:latest .
lint:
	uv run ruff check src/ tests/
format:
	uv run ruff format src/ tests/
typecheck:
	uv run mypy src/
