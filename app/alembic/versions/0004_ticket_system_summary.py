"""tickets.system_summary: resource-usage/specs snapshot collected via Hive
Desktop at ticket-creation time. NULL for tickets created from a plain
browser (no OS-level access to collect real specs from there).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE tickets ADD COLUMN system_summary JSONB NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE tickets DROP COLUMN IF EXISTS system_summary")
