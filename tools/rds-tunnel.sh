#!/bin/bash
# Opens a local port-forwarding tunnel to the REAL RDS instance via SSM
# Session Manager -- for occasional debugging against real data only.
# No VPN, no bastion host, no opening the database to the internet: access
# is governed entirely by IAM (who can start an SSM session on the app
# instance), and it's logged in CloudTrail.
#
# This is NOT how routine local development should work -- use
# `docker compose up` for that (a disposable local database you can reset
# freely). Only reach for this when you specifically need to look at real
# production data.
#
# Usage: ./tools/rds-tunnel.sh [local-port]
# Leave it running in its own terminal; connect to localhost:<local-port>
# with any Postgres client in a second terminal, or via a throwaway
# container if you don't have psql installed locally:
#   docker run --rm -it postgres:16 psql -h host.docker.internal -p <local-port> -U msp_app -d mspportal
set -e

LOCAL_PORT="${1:-5433}"

echo "Looking up the running app instance..."
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:DeployApp,Values=msp-portal" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)

echo "Looking up the RDS endpoint..."
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier msp-portal-db \
  --query 'DBInstances[0].Endpoint.Address' --output text)

echo ""
echo "Tunnel: localhost:$LOCAL_PORT -> $RDS_ENDPOINT:5432 (via $INSTANCE_ID)"
echo ""
echo "In another terminal, fetch the msp_app password:"
echo "  aws ssm get-parameter --name /msp-portal/db-url --with-decryption --query Parameter.Value --output text"
echo "  (the password is the segment between 'msp_app:' and '@' in that URL)"
echo ""
echo "Then connect with any Postgres client to localhost:$LOCAL_PORT, or:"
echo "  docker run --rm -it postgres:16 psql -h host.docker.internal -p $LOCAL_PORT -U msp_app -d mspportal"
echo ""

aws ssm start-session --target "$INSTANCE_ID" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$RDS_ENDPOINT\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"$LOCAL_PORT\"]}"
