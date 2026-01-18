#!/bin/bash
# Script to run database migrations

cd "$(dirname "$0")"

echo "Running Alembic migrations..."
source ../venv/bin/activate

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "Error: PostgreSQL is not running!"
    echo "Please start PostgreSQL first:"
    echo "  sudo systemctl start postgresql"
    exit 1
fi

# Run migrations
echo "Upgrading database to latest version..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✓ Migrations completed successfully!"
else
    echo "✗ Migration failed. Please check the error messages above."
    exit 1
fi

