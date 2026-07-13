"""remote_sessions: billable time tracking around external remote-support
tools (GoToAssist, Datto RMM, etc.) -- Hive does not perform the actual
remoting itself, only tracks Engineer-driven start/end clicks with a
30-second reconnect grace period.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE remote_sessions (
            id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            ticket_id        BIGINT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            org_id           BIGINT NOT NULL REFERENCES organizations(id),
            engineer_id      BIGINT NOT NULL REFERENCES users(id),
            started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            disconnected_at  TIMESTAMPTZ NULL,
            ended_at         TIMESTAMPTZ NULL,
            summary          TEXT NULL,
            CONSTRAINT remote_sessions_disconnect_after_start CHECK (disconnected_at IS NULL OR disconnected_at >= started_at),
            CONSTRAINT remote_sessions_end_requires_disconnect CHECK (ended_at IS NULL OR disconnected_at IS NOT NULL)
        )
        """
    )
    op.execute("CREATE INDEX remote_sessions_ticket_id_idx ON remote_sessions (ticket_id)")
    op.execute("CREATE INDEX remote_sessions_org_id_idx ON remote_sessions (org_id)")

    # Enforces "at most one open (Active/Grace) session per ticket" at the DB
    # level -- this is what makes the start-route atomic without row locking.
    op.execute(
        """
        CREATE UNIQUE INDEX remote_sessions_one_open_per_ticket
            ON remote_sessions (ticket_id) WHERE ended_at IS NULL
        """
    )

    # Denormalized org_id, identical rationale/shape to ticket_comments: keeps
    # the RLS predicate a flat column comparison, not a subquery into tickets.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_remote_session_org_id() RETURNS TRIGGER AS $$
        BEGIN
            SELECT org_id INTO NEW.org_id FROM tickets WHERE id = NEW.ticket_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER remote_sessions_set_org_id
        BEFORE INSERT ON remote_sessions
        FOR EACH ROW EXECUTE FUNCTION set_remote_session_org_id()
        """
    )

    op.execute("ALTER TABLE remote_sessions ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY remote_sessions_engineer_all ON remote_sessions
            USING      (current_setting('app.current_role', true) = 'engineer')
            WITH CHECK (current_setting('app.current_role', true) = 'engineer')
        """
    )
    op.execute(
        """
        CREATE POLICY remote_sessions_client_own_org ON remote_sessions FOR SELECT
            USING (
                current_setting('app.current_role', true) = 'client'
                AND org_id = current_setting('app.current_org_id', true)::bigint
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS remote_sessions CASCADE")
    op.execute("DROP FUNCTION IF EXISTS set_remote_session_org_id CASCADE")
