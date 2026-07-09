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
