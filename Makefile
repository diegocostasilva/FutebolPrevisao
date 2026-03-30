VENV := /opt/mcp-platform/venv
PYTHON := $(VENV)/bin/python
PY := $(VENV)/bin

# ── Environment ───────────────────────────────────────────────────────────────

.PHONY: venv
venv:
	python3.12 -m venv $(VENV)
	$(PY)/pip install --upgrade pip
	$(PY)/pip install -r requirements.txt

# ── Tests ─────────────────────────────────────────────────────────────────────

.PHONY: test
test:
	$(PY)/pytest

.PHONY: test-unit
test-unit:
	$(PY)/pytest tests/unit/ -v

.PHONY: test-integration
test-integration:
	$(PY)/pytest tests/integration/ -v

.PHONY: test-cov
test-cov:
	$(PY)/pytest --cov=src --cov-report=term-missing --cov-report=html

# ── Code quality ──────────────────────────────────────────────────────────────

.PHONY: lint
lint:
	$(PY)/ruff check .

.PHONY: format
format:
	$(PY)/ruff format .

.PHONY: typecheck
typecheck:
	$(PY)/mypy .

.PHONY: check
check: lint typecheck

.PHONY: pre-commit
pre-commit:
	$(PY)/pre-commit run --all-files

# ── Infrastructure ────────────────────────────────────────────────────────────

.PHONY: up
up:
	bash setup.sh

.PHONY: up-postgres
up-postgres:
	docker compose --project-directory . -f infra/docker/docker-compose.postgres.yml up -d

.PHONY: up-redis
up-redis:
	docker compose --project-directory . -f infra/docker/docker-compose.redis.yml up -d

.PHONY: up-airflow
up-airflow:
	docker compose --project-directory . -f infra/docker/docker-compose.airflow.yml up -d

.PHONY: up-spark
up-spark:
	docker compose --project-directory . -f infra/docker/docker-compose.spark.yml up -d

.PHONY: down
down:
	docker compose --project-directory . -f infra/docker/docker-compose.airflow.yml down
	docker compose --project-directory . -f infra/docker/docker-compose.spark.yml down
	docker compose --project-directory . -f infra/docker/docker-compose.redis.yml down
	docker compose --project-directory . -f infra/docker/docker-compose.postgres.yml down

.PHONY: ps
ps:
	docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# ── dbt ───────────────────────────────────────────────────────────────────────

.PHONY: dbt-run
dbt-run:
	cd dbt && $(PY)/dbt run

.PHONY: dbt-test
dbt-test:
	cd dbt && $(PY)/dbt test

.PHONY: dbt-docs
dbt-docs:
	cd dbt && $(PY)/dbt docs generate && $(PY)/dbt docs serve

# ── Utilities ─────────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage
