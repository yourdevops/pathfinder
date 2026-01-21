#!/bin/bash
# Entrypoint script for SSP container

set -e

echo "Starting Self-Service Portal..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files (if not already done)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start gunicorn
echo "Starting gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 ssp.wsgi:application
