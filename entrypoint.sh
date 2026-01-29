#!/bin/bash
# Entrypoint script for SSP container

set -e

echo "Starting Developer Self-Service Portal..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files (if not already done)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start uvicorn (ASGI server)
echo "Starting uvicorn server..."
exec uvicorn pathfinder.asgi:application --host 0.0.0.0 --port 8000 --workers 2
