-- Runs automatically on first startup of the local Postgres container (via
-- docker-entrypoint-initdb.d). Mirrors the one-time manual `CREATE ROLE
-- msp_app` bootstrap step required in production before the first Alembic
-- migration can succeed (0001_initial_schema.py GRANTs to msp_app) --
-- automated here since there's no equivalent "run once by hand" step that
-- makes sense for a disposable local dev database.
CREATE ROLE msp_app LOGIN PASSWORD 'localdev' NOSUPERUSER NOBYPASSRLS;
