FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false POETRY_NO_INTERACTION=1
WORKDIR /app
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
# poetry.lock (lock-version 2.1) requires Poetry >= 2.1; keep the Docker pin in sync.
COPY pyproject.toml poetry.lock README.md ./
COPY src ./src
RUN poetry install --only main --no-root && pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 triavoz
USER triavoz
CMD ["python", "-m", "triavoz_agent.main", "start"]
