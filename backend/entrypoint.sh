#!/usr/bin/env bash
set -euo pipefail

echo "=== Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} ==="
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
  echo "  db not ready, retrying in 2s..."
  sleep 2
done
echo "  db is ready."

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --clear

echo "=== Ensuring superuser exists ==="
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('ADMIN_DJANGO_USERNAME', '')
password = os.environ.get('ADMIN_DJANGO_PASSWORD', '')
if username and password:
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, '', password)
        print(f'  Superuser \"{username}\" created.')
    else:
        print(f'  Superuser \"{username}\" already exists.')
else:
    print('  ADMIN_DJANGO_USERNAME/PASSWORD not set — skipping.')
"

echo "=== Starting Gunicorn ==="
exec gunicorn backend.wsgi:application -c gunicorn.conf.py
