from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


def _fetch_ssm_parameter(name: str) -> str | None:
    """Best-effort SSM lookup. Returns None (not raise) on any failure so
    local dev without AWS credentials can fall back to env vars."""
    try:
        import boto3

        client = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        response = client.get_parameter(Name=name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception:
        return None


class Settings(BaseSettings):
    database_url: str
    cookie_secure: bool = False
    session_idle_hours: int = 8
    session_absolute_days: int = 7


@lru_cache
def get_settings() -> Settings:
    project_name = os.environ.get("PROJECT_NAME", "msp-portal")

    database_url = os.environ.get("DATABASE_URL") or _fetch_ssm_parameter(f"/{project_name}/db-url")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set and could not be fetched from SSM parameter "
            f"/{project_name}/db-url. Set DATABASE_URL for local development."
        )

    cookie_secure_raw = os.environ.get("COOKIE_SECURE") or _fetch_ssm_parameter(f"/{project_name}/cookie-secure") or "false"

    return Settings(
        database_url=database_url,
        cookie_secure=str(cookie_secure_raw).strip().lower() == "true",
    )
