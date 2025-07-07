#!/usr/bin/env bash
# Exit on error
set -o errexit

# Run the import script to populate the database
# The database tables will be created automatically by the script.
python scripts/import_data.py

# Start the Gunicorn server
gunicorn app:app -b 0.0.0.0:$PORT
