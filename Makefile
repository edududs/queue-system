# Simple project Makefile (focus on api/ subproject)

UV := uv
HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: help setup typecheck lint fmt test run dev clean

help:
	@echo "Available targets:"
	@echo "  setup       - Sync dependencies (incl. dev) with uv in api/"
	@echo "  typecheck   - Run mypy with auto-install of stubs in api/"
	@echo "  lint        - Run ruff check in api/"
	@echo "  fmt         - Run ruff format and sort imports (isort via ruff) in api/"
	@echo "  test        - Run pytest in api/"
	@echo "  run         - Run FastAPI with uvicorn in api/ (reload)"
	@echo "  dev         - Alias for run"
	@echo "  clean       - Remove caches in api/"

setup:
	cd api && $(UV) sync --group dev

typecheck:
	cd api && $(UV) run --group dev mypy --install-types --non-interactive

lint:
	cd api && $(UV) run --group dev ruff check .

fmt:
	cd api && $(UV) run --group dev ruff format .
	cd api && $(UV) run --group dev ruff check . --select I --fix

test:
	cd api && $(UV) run --group dev pytest -q

run:
	cd api && $(UV) run --group dev uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

dev: run

config: setup typecheck lint fmt test

clean:
	find api -type d -name __pycache__ -exec rm -rf {} +
	rm -rf api/.pytest_cache
