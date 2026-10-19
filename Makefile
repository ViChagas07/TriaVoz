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

test-agent:
	cd apps/agent && poetry run pytest

lint:
	cd apps/api && poetry run ruff check src tests migrations && poetry run mypy src
	cd apps/agent && poetry run ruff check src tests && poetry run mypy src
	cd apps/web && npm run typecheck

graph:
	graphify .

.PHONY: up down reset-db migrate test-api test-agent lint graph
