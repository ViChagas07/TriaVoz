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

seed:
	cd apps/api && poetry run python scripts/seed_demo.py

test-agent:
	cd apps/agent && poetry run pytest

test-mutations:
	cd apps/api && poetry run python ../../scripts/verify_rls_mutations.py

lint:
	cd apps/api && poetry run ruff check src tests migrations scripts && poetry run mypy src
	cd apps/agent && poetry run ruff check src tests && poetry run mypy src
	cd apps/web && npm run typecheck

graph:
	graphify .

.PHONY: up down reset-db migrate seed test-api test-agent test-mutations lint graph
