# SalesIQ developer commands.
PY := .venv/Scripts/python.exe
ifeq ($(OS),)
PY := .venv/bin/python
endif

.DEFAULT_GOAL := help
.PHONY: help setup dev test test-fast lint format typecheck security audit bench docker-build docker-up docker-down clean secret

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

setup:  ## Create the venv and install dev dependencies
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt
	@test -f .env || cp .env.example .env

dev:  ## Run the API with autoreload
	$(PY) -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

test:  ## Run the full test suite
	$(PY) -m pytest

test-fast:  ## Run tests that need no external services
	$(PY) -m pytest -m "not integration"

lint:  ## Lint
	$(PY) -m ruff check .

format:  ## Auto-format and fix imports
	$(PY) -m ruff format .
	$(PY) -m ruff check . --fix

typecheck:  ## Type check the typed modules
	$(PY) -m mypy config observability utils api --ignore-missing-imports

security:  ## Static security analysis
	$(PY) -m bandit -r . -x ./tests,./.venv,./frontend -ll

audit:  ## Dependency vulnerability audit
	$(PY) -m pip_audit -r requirements.txt

bench:  ## Run microbenchmarks (needs Redis for the cache suite)
	TEST_REDIS_URL=redis://localhost:6379/14 $(PY) benchmarks/bench.py --json benchmarks/results.json

secret:  ## Generate a production API_SECRET_KEY
	@$(PY) -c "import secrets; print(secrets.token_urlsafe(32))"

docker-build:  ## Build the container image
	docker build -t salesiq-api:local .

docker-up:  ## Start the local stack
	docker compose up -d --build

docker-down:  ## Stop the local stack
	docker compose down

clean:  ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
