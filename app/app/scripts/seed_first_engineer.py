"""One-time CLI bootstrap: creates the first Engineer account.

Not a web route -- there is no open self-registration endpoint. Run once,
manually, via SSM RunCommand after the first successful deployment:

    aws ssm send-command --document-name AWS-RunShellScript \\
      --targets "Key=tag:DeployApp,Values=msp-portal" \\
      --parameters commands="/opt/msp-portal-venv/bin/python -m app.scripts.seed_first_engineer --email you@example.com --name 'First Engineer'"

Connects with the dbadmin/migrator credential (DATABASE_ADMIN_URL env var or
the /{project}/db-admin-url SSM parameter), not the app's msp_app runtime
credential -- consistent with env.py's migration connection.

Refuses to run if an Engineer already exists, so re-invoking this command
later (e.g. by mistake) is a safe no-op rather than a way to mint rogue
accounts.
"""
from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine, text

from app.auth.security import generate_temp_password, hash_password
from app.config import _fetch_ssm_parameter


def _admin_database_url() -> str:
    url = os.environ.get("DATABASE_ADMIN_URL")
    if url:
        return url
    project_name = os.environ.get("PROJECT_NAME", "msp-portal")
    url = _fetch_ssm_parameter(f"/{project_name}/db-admin-url")
    if not url:
        print(
            f"DATABASE_ADMIN_URL is not set and could not be fetched from SSM "
            f"parameter /{project_name}/db-admin-url.",
            file=sys.stderr,
        )
        sys.exit(1)
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, dest="full_name")
    args = parser.parse_args()

    engine = create_engine(_admin_database_url())
    with engine.begin() as conn:
        existing_engineer = conn.execute(
            text("SELECT COUNT(*) FROM users WHERE role = 'engineer'")
        ).scalar_one()
        if existing_engineer > 0:
            print(
                "Refusing to run: at least one Engineer account already exists. "
                "Create additional Engineers by hand if needed.",
                file=sys.stderr,
            )
            sys.exit(1)

        existing_email = conn.execute(
            text("SELECT 1 FROM users WHERE lower(email) = lower(:email)"),
            {"email": args.email},
        ).first()
        if existing_email:
            print(f"A user with email {args.email} already exists.", file=sys.stderr)
            sys.exit(1)

        temp_password = generate_temp_password()
        conn.execute(
            text(
                """
                INSERT INTO users (org_id, role, email, password_hash, full_name)
                VALUES (NULL, 'engineer', :email, :password_hash, :full_name)
                """
            ),
            {
                "email": args.email.strip().lower(),
                "password_hash": hash_password(temp_password),
                "full_name": args.full_name.strip(),
            },
        )

    print(f"Engineer account created: {args.email}")
    print(f"Temporary password (shown once): {temp_password}")


if __name__ == "__main__":
    main()
