#!/bin/bash
# Script to run Alembic migrations
# Make sure your database is running and .env file is configured before running this script

set -e

# Activate virtual environment
source ../venv/bin/activate

# Change to project directory
cd "$(dirname "$0")"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Using default database configuration."
    echo "Make sure DATABASE_URL is set in your environment or .env file."
fi

# Show current database URL (without password)
echo "Using DATABASE_URL from config..."
python -c "from app.core.config import settings; db_url = settings.DATABASE_URL; print('Database:', db_url.split('@')[1] if '@' in db_url else 'Not configured')"

# Check Alembic version
echo ""
echo "Current Alembic version:"
alembic current

# Generate new migration (if models changed)
echo ""
echo "Generating new migration (if models changed)..."
alembic revision --autogenerate -m "Auto migration"

# Apply migrations
echo ""
echo "Applying migrations..."
alembic upgrade head

echo ""
echo "Migrations completed successfully!"

