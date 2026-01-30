#!/bin/bash
# Run script for GoGoCar application

# Activate virtual environment
source ../venv/bin/activate

# Set environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --env-file ../.env
