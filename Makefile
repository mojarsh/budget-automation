.PHONY: install test lint format typecheck security build setup verify all

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

setup:
	bash infra/setup.sh
verify:
	@echo "--- ExecStart ---"
	@systemctl show budget-automation.service | grep ExecStart
	@echo "--- Group membership ---"
	@groups $(shell whoami)
	@echo "--- Linger ---"
	@loginctl show-user $(shell whoami) | grep Linger
	@echo "--- Runtime directory ---"
	@ls -la /run/user/$(shell id -u)/budget_tmp
	@echo "--- Timer status ---"
	@systemctl status budget-automation.timer --no-pager
all: format lint typecheck security test
