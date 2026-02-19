#!/bin/bash
# Entrypoint script for SSP container

set -e

echo "Starting Developer Self-Service Portal..."

# Run migrations
echo "Running database migrations..."
uv run python manage.py migrate --noinput

# Collect static files (if not already done)
echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

# Execute the CMD passed to the container
exec "$@"
