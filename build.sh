#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create superuser from environment variables (if set)
python manage.py create_superuser

# Import data if DJANGO_IMPORT_SCRIPT is True
if [ "$DJANGO_IMPORT_SCRIPT" = "True" ]; then
    echo "Importing buildings from CSV files..."
    python manage.py import_buildings territory/data/*.csv

    echo "Geocoding buildings..."
    python manage.py geocode_buildings
fi
