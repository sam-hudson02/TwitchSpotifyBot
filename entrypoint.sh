#!/bin/sh
set -e
python src/migrate.py
exec uvicorn --app-dir src server.app:app --host 0.0.0.0 --port 5000
