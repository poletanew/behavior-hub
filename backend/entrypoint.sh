#!/bin/sh
set -e

echo "Waiting for Postgres..."
until python -c "
import sys
import psycopg
from app.core.config import get_settings
url = get_settings().DATABASE_URL.replace('postgresql+psycopg://', 'postgresql://')
try:
    psycopg.connect(url).close()
except Exception as exc:
    print(exc)
    sys.exit(1)
"; do
  sleep 1
done

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
