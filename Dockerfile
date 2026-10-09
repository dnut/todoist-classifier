FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies, cached separately from application code
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Install application as a non-editable package
COPY todoist_classifier.py ./
RUN uv sync --locked --no-dev --no-editable


FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 10001:10001

CMD ["todoist-classifier"]
