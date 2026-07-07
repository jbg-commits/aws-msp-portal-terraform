"""initial schema: organizations, users, tickets, ticket_comments, sessions,
row-level security policies, and msp_app grants

Revision ID: 0001
Revises:
Create Date: 2026-07-07
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE organizations (
            id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name        TEXT NOT NULL,
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE users (
            id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            org_id         BIGINT NULL REFERENCES organizations(id),
            role           TEXT NOT NULL CHECK (role IN ('client','engineer')),
            email          TEXT NOT NULL,
            password_hash  TEXT NOT NULL,
            full_name      TEXT NOT NULL,
            is_active      BOOLEAN NOT NULL DEFAULT true,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT users_role_org_consistency CHECK (
                (role = 'client'   AND org_id IS NOT NULL) OR
                (role = 'engineer' AND org_id IS NULL)
            )
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX users_email_unique_idx ON users (lower(email))")
    op.execute("CREATE INDEX users_org_id_idx ON users (org_id)")

    op.execute(
        """
        CREATE TABLE tickets (
            id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            org_id                BIGINT NOT NULL REFERENCES organizations(id),
            title                 TEXT NOT NULL,
            description           TEXT NOT NULL,
            status                TEXT NOT NULL DEFAULT 'open'
                                    CHECK (status IN ('open','in_progress','waiting_on_client','resolved','closed')),
            priority              TEXT NOT NULL DEFAULT 'medium'
                                    CHECK (priority IN ('low','medium','high','urgent')),
            created_by            BIGINT NOT NULL REFERENCES users(id),
            assigned_engineer_id  BIGINT NULL REFERENCES users(id),
            created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX tickets_org_id_idx ON tickets (org_id)")
    op.execute("CREATE INDEX tickets_org_status_idx ON tickets (org_id, status)")
    op.execute("CREATE INDEX tickets_assigned_engineer_idx ON tickets (assigned_engineer_id)")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER tickets_set_updated_at
        BEFORE UPDATE ON tickets
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )

    op.execute(
        """
        CREATE TABLE ticket_comments (
            id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            ticket_id   BIGINT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            org_id      BIGINT NOT NULL REFERENCES organizations(id),
            author_id   BIGINT NOT NULL REFERENCES users(id),
            body        TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ticket_comments_ticket_id_idx ON ticket_comments (ticket_id)")
    op.execute("CREATE INDEX ticket_comments_org_id_idx ON ticket_comments (org_id)")

    # org_id is denormalized from the parent ticket so the RLS predicate on
    # ticket_comments is a flat column comparison, not a subquery into
    # tickets -- simpler, cheaper, and avoids cross-table RLS recursion.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_comment_org_id() RETURNS TRIGGER AS $$
        BEGIN
            SELECT org_id INTO NEW.org_id FROM tickets WHERE id = NEW.ticket_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER ticket_comments_set_org_id
        BEFORE INSERT ON ticket_comments
        FOR EACH ROW EXECUTE FUNCTION set_comment_org_id()
        """
    )

    # Sessions: deliberately NO row-level security. It's looked up by an
    # unguessable token (not a sequential id), so it isn't a cross-org
    # enumeration target, and it must be queryable before any org context
    # exists (the auth lookup that determines that context runs here first).
    op.execute(
        """
        CREATE TABLE sessions (
            id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            token         TEXT NOT NULL,
            user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role          TEXT NOT NULL,
            org_id        BIGINT NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at    TIMESTAMPTZ NOT NULL,
            revoked_at    TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX sessions_token_unique_idx ON sessions (token)")
    op.execute("CREATE INDEX sessions_user_id_idx ON sessions (user_id)")

    # ── Row-Level Security ────────────────────────────────────────────────
    #
    # Enabled on organizations/tickets/ticket_comments only -- NOT on users.
    # RLS on `users` would create a login deadlock: authenticating a user
    # requires reading `users` by email BEFORE their role/org is known (that's
    # the entire point of the lookup), so no RLS predicate on `users` could
    # ever be satisfied at that point. `users` visibility/write rules are
    # instead ordinary application-layer RBAC (see app/auth/dependencies.py,
    # app/routers/admin.py) -- consistent with the general principle that RLS
    # enforces the org boundary on client-facing ticket data specifically,
    # while capability/field-level rules live in the app layer.
    #
    # current_setting(name, true) returns NULL (not an error) when unset, so
    # a bug that forgets to set these session vars makes every policy below
    # evaluate to false/NULL -- fail-closed (zero rows), never a cross-org leak.

    for table in ("organizations", "tickets", "ticket_comments"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY organizations_engineer_all ON organizations
            USING      (current_setting('app.current_role', true) = 'engineer')
            WITH CHECK (current_setting('app.current_role', true) = 'engineer')
        """
    )
    op.execute(
        """
        CREATE POLICY organizations_client_own_org ON organizations FOR SELECT
            USING (
                current_setting('app.current_role', true) = 'client'
                AND id = current_setting('app.current_org_id', true)::bigint
            )
        """
    )

    op.execute(
        """
        CREATE POLICY tickets_engineer_all ON tickets
            USING      (current_setting('app.current_role', true) = 'engineer')
            WITH CHECK (current_setting('app.current_role', true) = 'engineer')
        """
    )
    op.execute(
        """
        CREATE POLICY tickets_client_own_org ON tickets
            USING (
                current_setting('app.current_role', true) = 'client'
                AND org_id = current_setting('app.current_org_id', true)::bigint
            )
            WITH CHECK (
                current_setting('app.current_role', true) = 'client'
                AND org_id = current_setting('app.current_org_id', true)::bigint
            )
        """
    )

    op.execute(
        """
        CREATE POLICY ticket_comments_engineer_all ON ticket_comments
            USING      (current_setting('app.current_role', true) = 'engineer')
            WITH CHECK (current_setting('app.current_role', true) = 'engineer')
        """
    )
    op.execute(
        """
        CREATE POLICY ticket_comments_client_own_org ON ticket_comments
            USING (
                current_setting('app.current_role', true) = 'client'
                AND org_id = current_setting('app.current_org_id', true)::bigint
            )
            WITH CHECK (
                current_setting('app.current_role', true) = 'client'
                AND org_id = current_setting('app.current_org_id', true)::bigint
            )
        """
    )

    # ── Runtime role grants ──────────────────────────────────────────────
    # msp_app is created out-of-band (one-time manual bootstrap, see the
    # project runbook) before this migration ever runs -- it must already
    # exist for these GRANTs to succeed.
    op.execute("GRANT CONNECT ON DATABASE mspportal TO msp_app")
    op.execute("GRANT USAGE ON SCHEMA public TO msp_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO msp_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO msp_app")
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES FOR ROLE dbadmin IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO msp_app
        """
    )
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES FOR ROLE dbadmin IN SCHEMA public
            GRANT USAGE, SELECT ON SEQUENCES TO msp_app
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ticket_comments CASCADE")
    op.execute("DROP TABLE IF EXISTS tickets CASCADE")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS organizations CASCADE")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at CASCADE")
    op.execute("DROP FUNCTION IF EXISTS set_comment_org_id CASCADE")
