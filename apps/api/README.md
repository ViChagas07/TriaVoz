# TriaVoz API

FastAPI backend. Clean Architecture: `domain` → `application` → `infrastructure` / `interfaces`.
See `../../docs/context/CONTEXT.md` for the full spec and `../../docs/agent/PROGRESS.md` for status.

```bash
poetry install
poetry run alembic upgrade head          # as triavoz_owner (TRIAVOZ_DATABASE_URL_OWNER)
poetry run uvicorn triavoz.main:app --reload
poetry run pytest                         # DB tests need TRIAVOZ_TEST_* env vars (see tests/conftest.py)
```
