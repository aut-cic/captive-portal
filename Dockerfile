# Python 3.14 base to match the project lockfile
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENV=.venv

WORKDIR /app

# System deps for building MySQL client libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies with uv in a locked, non-dev environment
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

# App source
COPY CaptivePortal ./CaptivePortal
COPY README.md .

ENV DJANGO_SETTINGS_MODULE=src.settings \
    PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

# Note: configure database credentials via env vars or override settings in production.
CMD ["uv", "run", "python", "CaptivePortal/manage.py", "runserver", "0.0.0.0:8000"]
