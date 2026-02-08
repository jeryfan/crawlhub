#!/bin/bash

set -e

source /workspace/.venv/bin/activate

function run_migrations() {
  echo "Running database migrations..."
  alembic upgrade head
  echo "Database migrations completed."
}

function start_serve() {
  while true; do
    if [ "$DEBUG" = "true" ]; then
      uvicorn app:app --host 0.0.0.0 --port 8000 --reload
    else
      uvicorn app:app --host 0.0.0.0 --port 8000
    fi
  done
}

function start_worker() {
  while true; do
    exec celery -A app.celery worker --loglevel=info --pool=eventlet --concurrency=1000 &
    wait -n
  done
}

function start_beat() {
  while true; do
    exec celery -A app.celery beat --loglevel=info &
    wait -n
  done
}

case "${MODE}" in
"server")
  echo "Starting server"
  run_migrations
  start_serve &
  ;;
"worker")
  echo "Starting worker"
  start_worker &
  ;;
  "beat")
  echo "Starting beat"
  start_beat &
  ;;
esac

wait
