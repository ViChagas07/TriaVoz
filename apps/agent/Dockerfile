FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.4.1 POETRY_VIRTUALENVS_IN_PROJECT=1 POETRY_NO_INTERACTION=1
WORKDIR /app
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
# poetry.lock (lock-version 2.1) requires Poetry >= 2.1; keep the Docker pin in sync.
COPY pyproject.toml poetry.lock README.md ./
COPY src ./src
RUN poetry install --only main \
 && rm -rf .venv/lib/python3.11/site-packages/pip \
           .venv/lib/python3.11/site-packages/pip-*.dist-info \
           .venv/lib/python3.11/site-packages/setuptools \
           .venv/lib/python3.11/site-packages/setuptools-*.dist-info \
           .venv/lib/python3.11/site-packages/wheel \
           .venv/lib/python3.11/site-packages/wheel-*.dist-info \
           .venv/lib/python3.11/site-packages/jaraco \
           .venv/lib/python3.11/site-packages/jaraco.context-*.dist-info

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN useradd --create-home --uid 10001 triavoz \
 && rm -rf /usr/local/lib/python3.11/site-packages/pip* \
           /usr/local/lib/python3.11/site-packages/setuptools* \
           /usr/local/lib/python3.11/site-packages/wheel* \
           /usr/local/lib/python3.11/site-packages/pkg_resources \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.11
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src
USER triavoz
CMD ["python", "-m", "triavoz_agent.main", "start"]
