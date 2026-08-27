#!/bin/sh
set -e
python src/migrate.py
exec python src/server.py
