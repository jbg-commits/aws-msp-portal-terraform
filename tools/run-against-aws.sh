#!/bin/bash
# Runs the app in Docker pointed at the REAL AWS database, through the
# tunnel opened by tools/rds-tunnel.sh (must already be running in another
# terminal, forwarding localhost:5433 -> the real RDS instance).
#
# Fetches credentials fresh from SSM every run -- nothing is ever written
# to disk or committed to git. This makes localhost:8081 write directly
# to the real production database: there is no "undo" here. Anything you
# create (organizations, tickets, users) is real, the same way it would
# be if you'd done it at the real ALB URL.
set -e
export MSYS_NO_PATHCONV=1

echo "Fetching database credentials from SSM..."
APP_URL=$(aws ssm get-parameter --name /msp-portal/db-url --with-decryption --query Parameter.Value --output text)
ADMIN_URL=$(aws ssm get-parameter --name /msp-portal/db-admin-url --with-decryption --query Parameter.Value --output text)

APP_PASS=$(echo "$APP_URL" | sed -E 's#.*msp_app:([^@]+)@.*#\1#')
ADMIN_PASS=$(echo "$ADMIN_URL" | sed -E 's#.*dbadmin:([^@]+)@.*#\1#')

export DATABASE_URL="postgresql+psycopg2://msp_app:${APP_PASS}@host.docker.internal:5433/mspportal"
export DATABASE_ADMIN_URL="postgresql+psycopg2://dbadmin:${ADMIN_PASS}@host.docker.internal:5433/mspportal"

echo ""
echo "=============================================================="
echo " This runs the app locally but writes to the REAL AWS database."
echo " Make sure tools/rds-tunnel.sh is already running in another"
echo " terminal, or this will fail to connect."
echo "=============================================================="
echo ""

docker compose -f docker-compose.aws.yml up --build
