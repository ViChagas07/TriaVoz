# TriaVoz API

FastAPI backend. Clean Architecture: `domain` → `application` → `infrastructure` / `interfaces`.
See `../../docs/context/CONTEXT.md` for the full spec and `../../docs/agent/PROGRESS.md` for status.

```bash
poetry install
poetry run alembic upgrade head          # as triavoz_owner (TRIAVOZ_DATABASE_URL_OWNER)
poetry run uvicorn triavoz.main:app --reload
poetry run pytest                         # DB tests need TRIAVOZ_TEST_* env vars (see tests/conftest.py)
poetry run pytest --cov=triavoz --cov-report=term-missing --cov-fail-under=85
poetry run pytest tests/isolation         # blocking tenant-isolation gate
poetry run python -m evals                # deterministic agent evals (needs the same test DB)
```

`GET /metrics` is the Prometheus endpoint. See `../../docs/observability.md` and
`../../docs/evals.md`.
