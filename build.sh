#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Run Django migrations (essential for sessions)
python manage.py migrate

# Fix vector dimensions (drops and recreates tables with correct dimensions)
python fix_vector_dimensions.py

# Run database initialization (creates extensions and tables)
python manage.py init_db
