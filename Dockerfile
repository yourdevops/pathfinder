FROM python:3.13-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Create non-root user for security
RUN groupadd --gid 1000 ssp && \
    useradd --uid 1000 --gid ssp --shell /bin/bash --create-home ssp

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY --chown=ssp:ssp . .

# Create necessary directories and make entrypoint executable
RUN mkdir -p /app/staticfiles /app/data && \
    chmod +x /app/entrypoint.sh && \
    chown -R ssp:ssp /app

# Switch to non-root user
USER ssp

# Collect static files (build-time only, real SECRET_KEY injected at runtime)
RUN DJANGO_SECRET_KEY=build-time-placeholder uv run python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run via entrypoint (handles migrations)
ENTRYPOINT ["/app/entrypoint.sh"]
