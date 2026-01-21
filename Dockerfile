FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd --gid 1000 ssp && \
    useradd --uid 1000 --gid ssp --shell /bin/bash --create-home ssp

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=ssp:ssp . .

# Create necessary directories and make entrypoint executable
RUN mkdir -p /app/staticfiles /app/manifests /app/data && \
    chmod +x /app/entrypoint.sh && \
    chown -R ssp:ssp /app

# Switch to non-root user
USER ssp

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run via entrypoint (handles migrations)
ENTRYPOINT ["/app/entrypoint.sh"]
