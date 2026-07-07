from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import _fetch_ssm_parameter
from app.db.base import Base

# Import all models so Base.metadata is fully populated (autogenerate support).
from app.models import organization, ticket, ticket_comment, user  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _migrator_database_url() -> str:
    """Migrations run as the dbadmin/table-owner role (bypasses RLS, needed
    for DDL and GRANTs) -- deliberately NOT the app's msp_app runtime
    credential from app.config.get_settings()."""
    url = os.environ.get("DATABASE_ADMIN_URL")
    if url:
        return url
    project_name = os.environ.get("PROJECT_NAME", "msp-portal")
    url = _fetch_ssm_parameter(f"/{project_name}/db-admin-url")
    if not url:
        raise RuntimeError(
            "DATABASE_ADMIN_URL is not set and could not be fetched from SSM "
            f"parameter /{project_name}/db-admin-url."
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_migrator_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _migrator_database_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
