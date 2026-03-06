test:
	uv run pytest

build:
	sudo docker build -t budget_automation:latest .
