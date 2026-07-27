#!/bin/sh
# Corre las migraciones pendientes antes de levantar el servidor.
# Simple y suficiente para el MVP (1 usuario, pocas instancias concurrentes);
# si el equipo crece, esto se separa a un paso previo del pipeline de CI/CD
# (ej. un job de Cloud Run dedicado a migraciones) en vez de correr en cada arranque.
set -e

echo "Aplicando migraciones de base de datos..."
alembic upgrade head

echo "Iniciando servidor..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
