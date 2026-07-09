# aws-msp-portal-terraform

## Local development

Run the ticketing app + a local Postgres with Docker Compose — no AWS account needed:

```
docker compose up --build
```

This builds `app/Dockerfile`, starts a `postgres:16` container (with the `msp_app`
role auto-created via `docker/init-msp-app-role.sql`, mirroring the one-time
manual bootstrap step required in production), runs the Alembic migration, and
starts the app at http://localhost:8081.

Seed a local Engineer account:

```
docker compose exec app python -m app.scripts.seed_first_engineer --email you@example.com --name "Your Name"
```

The printed temporary password is for the local database only.

To reset to a clean local database:

```
docker compose down -v
```

`app/config.py` and `app/alembic/env.py` prefer the `DATABASE_URL` /
`DATABASE_ADMIN_URL` env vars (set in `docker-compose.yml`) over fetching from
SSM Parameter Store, so local runs never touch AWS.

## Connecting to the real database (occasional debugging only)

Local dev should almost always use `docker compose up` above -- a disposable
database you can reset freely. For the rare case where you need to look at
real production data, `tools/rds-tunnel.sh` opens a port-forwarding tunnel to
the real RDS instance via SSM Session Manager: no VPN, no bastion host, no
opening the database to the internet -- access is governed by IAM (who can
start a session on the app instance) and logged in CloudTrail.

Requires the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
for the AWS CLI, and your AWS credentials configured locally.

```
./tools/rds-tunnel.sh
```

Leave it running in its own terminal. In a second terminal, fetch the
`msp_app` password and connect with any Postgres client to `localhost:5433`,
or use a throwaway container if you don't have `psql` installed:

```
aws ssm get-parameter --name /msp-portal/db-url --with-decryption --query Parameter.Value --output text
docker run --rm -it postgres:16 psql -h host.docker.internal -p 5433 -U msp_app -d mspportal
```

Treat this as read-only in practice -- there's no `docker compose down -v`
undo button against the real database.

## Running the app locally against the REAL database

If you want `localhost:8081` itself to read/write the real AWS database
(not a local sandbox), use `docker-compose.aws.yml` instead of the default
compose file:

1. In one terminal, open the tunnel and leave it running:
   ```
   ./tools/rds-tunnel.sh
   ```
2. In another terminal, from the repo root:
   ```
   ./tools/run-against-aws.sh
   ```

`run-against-aws.sh` fetches the real `msp_app`/`dbadmin` credentials fresh
from SSM every run (never written to disk or git) and points the app at
`host.docker.internal:5433` -- the tunnel from step 1. The app then runs
exactly like `docker compose up`, except every organization, ticket, and
user you create through `localhost:8081` is written directly to the real
RDS instance, the same as if you'd used the real ALB URL.

There is no local/prod separation in this mode -- it behaves like an
ordinary hosted application with a local frontend. Stop it with Ctrl+C or
`docker compose -f docker-compose.aws.yml down` (no `-v`; there's no local
volume to reset in this mode since nothing is stored locally).
