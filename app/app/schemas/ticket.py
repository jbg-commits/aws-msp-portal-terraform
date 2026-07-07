from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.ticket import PRIORITIES, STATUSES


class TicketCreate(BaseModel):
    """What ANY authenticated user (Client or Engineer) may submit to create a
    ticket. Deliberately has no org_id/status/priority/assigned_engineer_id --
    those are always set server-side, never trusted from client input."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)


class TicketStatusUpdate(BaseModel):
    """Engineer-only. Enforced by which router this schema is used in, not
    by anything in the schema itself."""

    status: str
    priority: str
    assigned_engineer_id: int | None = None

    def validate_choices(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"invalid status: {self.status}")
        if self.priority not in PRIORITIES:
            raise ValueError(f"invalid priority: {self.priority}")


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
