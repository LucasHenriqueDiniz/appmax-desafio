#!/bin/sh
set -e

echo "[boot] aplicando migrations..."
alembic upgrade head

echo "[boot] executando seed (idempotente)..."
python -m app.seed

echo "[boot] iniciando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
