up:
	docker compose up --build

down:
	docker compose down

reset-db:
	docker compose down -v

migrate:
	docker compose run --rm migrate

test-api:
	cd apps/api && poetry run pytest

test-coverage:
	cd apps/api && poetry run pytest --cov=triavoz --cov-report=term-missing --cov-fail-under=85

test-isolation:
	cd apps/api && poetry run pytest tests/isolation

test-e2e:
	cd apps/web && npm run test:e2e

seed:
	cd apps/api && poetry run python scripts/seed_demo.py

test-agent:
	cd apps/agent && poetry run pytest

# Needs TRIAVOZ_TEST_OWNER_DSN + TRIAVOZ_TEST_APP_DSN (+ optional TRIAVOZ_TEST_REDIS_URL)
# pointing at a migrated PostgreSQL database. Results: apps/api/evals/results/latest.{json,md}
evals:
	cd apps/api && poetry run python -m evals

observability:
	docker compose --profile observability up -d prometheus grafana

# LGPD retention/expurgo (runs as triavoz_ops; needs TRIAVOZ_DATABASE_URL_OPS)
purge-retention:
	cd apps/api && poetry run python scripts/purge_retention.py

test-mutations:
	cd apps/api && poetry run python ../../scripts/verify_rls_mutations.py

lint:
	cd apps/api && poetry run ruff check src tests migrations scripts evals && poetry run ruff format --check src tests migrations scripts evals && poetry run mypy src
	cd apps/agent && poetry run ruff check src tests && poetry run mypy src
	cd apps/web && npm run typecheck

# Local mirror of the blocking security gates in CI.
security:
	docker run --rm -v "$(CURDIR):/repo" zricethezav/gitleaks:v8.28.0 detect --source /repo --redact
	cd apps/api && poetry export --without-hashes -f requirements.txt -o /tmp/api-req.txt && python -m pip_audit -r /tmp/api-req.txt
	cd apps/agent && poetry export --without-hashes -f requirements.txt -o /tmp/agent-req.txt && python -m pip_audit -r /tmp/agent-req.txt
	cd apps/web && npm audit --omit=dev --audit-level=high
	docker run --rm -v "$(CURDIR):/work" aquasec/trivy:0.58.1 config --severity HIGH,CRITICAL --exit-code 1 --skip-dirs '**/node_modules' --skip-dirs '**/.next' /work

graph:
	graphify .

.PHONY: up down reset-db migrate seed test-api test-coverage test-isolation test-e2e test-agent evals observability purge-retention test-mutations lint graph security
