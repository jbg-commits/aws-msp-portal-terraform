"""human-readable ticket display IDs: T[YYMMDD].[daily sequence]

A dedicated counter table with an atomic INSERT ... ON CONFLICT DO UPDATE
gives a race-condition-safe, globally-shared, per-day-resetting sequence --
two tickets created in the same instant can never collide, without needing
application-level locking. Display-only: routing/URLs still use tickets.id
(the internal PK the RLS/IDOR security model in 0001 was built and tested
against) -- this migration never touches that.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-09
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No RLS needed here (like sessions) -- just a counter, not org-scoped
    # client data. New tables created by dbadmin automatically inherit the
    # msp_app grants via the ALTER DEFAULT PRIVILEGES rule set up in 0001.
    op.execute(
        """
        CREATE TABLE daily_ticket_sequences (
            day           DATE PRIMARY KEY,
            last_sequence INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    op.execute("ALTER TABLE tickets ADD COLUMN display_id TEXT")

    # Backfill existing tickets: number them in creation order within each
    # calendar day they were actually created on.
    op.execute(
        """
        WITH numbered AS (
            SELECT id, created_at::date AS day,
                   ROW_NUMBER() OVER (PARTITION BY created_at::date ORDER BY id) AS seq
            FROM tickets
        )
        UPDATE tickets t
        SET display_id = 'T' || to_char(numbered.day, 'YYMMDD') || '.' || numbered.seq
        FROM numbered
        WHERE t.id = numbered.id
        """
    )

    # Seed the counter table from the backfill so future tickets on a day
    # that already has historical tickets continue the sequence correctly
    # instead of colliding with the backfilled numbers.
    op.execute(
        """
        INSERT INTO daily_ticket_sequences (day, last_sequence)
        SELECT created_at::date, COUNT(*)
        FROM tickets
        GROUP BY created_at::date
        ON CONFLICT (day) DO NOTHING
        """
    )

    op.execute("ALTER TABLE tickets ALTER COLUMN display_id SET NOT NULL")
    op.execute("ALTER TABLE tickets ADD CONSTRAINT tickets_display_id_unique UNIQUE (display_id)")


def downgrade() -> None:
    op.execute("ALTER TABLE tickets DROP CONSTRAINT IF EXISTS tickets_display_id_unique")
    op.execute("ALTER TABLE tickets DROP COLUMN IF EXISTS display_id")
    op.execute("DROP TABLE IF EXISTS daily_ticket_sequences")
