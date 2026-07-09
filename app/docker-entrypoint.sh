#!/bin/sh
set -e

# Local dev only: production keeps "migrate" and "start" as separate
# CodeDeploy hooks (scripts/migrate.sh, scripts/start_server.sh) so a bad
# migration fails the deployment before traffic ever moves. There's no
# rollback concept for a local container, so combining them here is fine.
python -m alembic -c alembic.ini upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8080
