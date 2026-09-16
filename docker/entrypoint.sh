#!/bin/sh
set -e

# Apply migrations on start when asked (compose sets DJANGO_MIGRATE=1 for the web service).
# With several replicas, run migrations once as a separate job instead.
if [ "${DJANGO_MIGRATE:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

exec "$@"
