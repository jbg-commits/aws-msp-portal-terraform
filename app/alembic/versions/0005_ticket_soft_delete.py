"""tickets.deleted_at: soft-delete flag for tickets. NULL means active;
set to the deletion timestamp when an Engineer deletes a ticket, cleared
back to NULL on restore. Soft, not hard, delete -- preserves billing and
remote-session history and is fully reversible.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE tickets ADD COLUMN deleted_at TIMESTAMPTZ NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE tickets DROP COLUMN IF EXISTS deleted_at")
