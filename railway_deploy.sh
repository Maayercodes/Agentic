#!/bin/bash

# Railway deployment script
# This script runs necessary database migrations and initializations
# for deploying the application on Railway

set -e  # Exit on error

echo "Starting deployment process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Test database connection
echo "Testing database connection..."
python test_db_connection.py

# Run database migrations
echo "Running database migrations..."

# First initialize the database if needed
python src/database/init_db.py

# Then run the region column migration
python src/database/migrate_region_column.py

# Verify database
echo "Verifying database..."
python verify_database.py

# Start the application
echo "Starting application..."
exec python app.py