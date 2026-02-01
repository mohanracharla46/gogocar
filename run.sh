#!/bin/bash
# Production run script for Render

# Default to port 8000 if $PORT is not set
PORT="${PORT:-8000}"

echo "Starting GoGoCar on port $PORT..."

# Run migrations if needed
# alembic upgrade head

# Start gunicorn with uvicorn workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT
