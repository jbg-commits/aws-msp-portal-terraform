from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

SESSION_COOKIE_NAME = "session"


class NotAuthenticated(Exception):
    """No valid session cookie. Handled in main.py -> redirect to /login."""


class Forbidden(Exception):
    """Authenticated, but the caller's role doesn't permit this action."""


@dataclass
class CurrentUser:
    id: int
    role: str  # 'client' | 'engineer'
    org_id: int | None
    full_name: str
    email: str

    @property
    def is_engineer(self) -> bool:
        return self.role == "engineer"


def _set_rls_context(db: Session, role: str, org_id: int | None) -> None:
    """Scope the rest of THIS transaction's queries to this caller.

    Uses SET LOCAL (transaction-scoped, auto-cleared on commit/rollback) via
    bound parameters -- never SET, and never string-interpolated -- because
    the underlying connection is pooled and reused across different users'
    requests. This must run before any query against organizations/tickets/
    ticket_comments (the RLS-protected tables) in this request.
    """
    db.execute(text("SET LOCAL app.current_role = :role"), {"role": role})
    db.execute(
        text("SET LOCAL app.current_org_id = :org_id"),
        {"org_id": str(org_id) if org_id is not None else "0"},
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise NotAuthenticated()

    # `sessions` and `users` both have no RLS policies (see 0001_initial_schema.py
    # for why -- RLS on `users` would create a login chicken-and-egg deadlock),
    # so this lookup is safe to run before any RLS context is established.
    row = db.execute(
        text(
            """
            SELECT s.user_id, s.role, s.org_id, s.created_at, u.full_name, u.email, u.is_active
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = :token
              AND s.revoked_at IS NULL
              AND s.expires_at > now()
            """
        ),
        {"token": token},
    ).first()

    if row is None or not row.is_active:
        raise NotAuthenticated()

    # Sliding 8h idle expiry, capped at 7 days from session creation.
    db.execute(
        text(
            """
            UPDATE sessions
            SET last_seen_at = now(),
                expires_at = LEAST(now() + interval '8 hours', created_at + interval '7 days')
            WHERE token = :token
            """
        ),
        {"token": token},
    )

    user = CurrentUser(
        id=row.user_id,
        role=row.role,
        org_id=row.org_id,
        full_name=row.full_name,
        email=row.email,
    )

    _set_rls_context(db, user.role, user.org_id)

    return user


def require_engineer(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_engineer:
        raise Forbidden()
    return user
