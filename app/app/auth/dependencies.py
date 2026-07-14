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

    SET/SET LOCAL are Postgres utility statements, not regular SQL -- they
    do not accept bind parameters for the value (psycopg2 raises a syntax
    error if you try). set_config() is an ordinary function call and does
    accept parameters; is_local=true makes it behave exactly like SET LOCAL
    (transaction-scoped, auto-cleared on commit/rollback) -- required
    because the underlying connection is pooled and reused across different
    users' requests. This must run before any query against organizations/
    tickets/ticket_comments (the RLS-protected tables) in this request.
    """
    db.execute(text("SELECT set_config('app.current_role', :role, true)"), {"role": role})
    db.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": str(org_id) if org_id is not None else "0"},
    )


def _org_login_ok(db: Session, role: str, org_id: int | None) -> bool:
    """Engineers (org_id NULL) are always ok; clients are gated on their
    org's is_active. organizations carries RLS and no caller context exists
    yet at either call site (login, and the top of get_current_user before
    _set_rls_context runs) -- current_setting() returns NULL with no context
    set, closing every USING clause on organizations. Briefly presenting as
    'engineer' is safe: the result is only used as an internal boolean gate,
    never returned to the caller, and is overwritten by the real role right
    after (get_current_user) or discarded at transaction end (failed login).
    """
    if role != "client":
        return True
    # Postgres doesn't guarantee short-circuit evaluation of the AND inside
    # organizations_client_own_org's USING clause -- if app.current_org_id
    # is left unset, the ::bigint cast in that policy can still be evaluated
    # against an empty string and raise, even though current_role='engineer'
    # should make the whole clause irrelevant. Always set both configs
    # together, same as _set_rls_context does.
    db.execute(text("SELECT set_config('app.current_role', 'engineer', true)"))
    db.execute(text("SELECT set_config('app.current_org_id', '0', true)"))
    row = db.execute(text("SELECT is_active FROM organizations WHERE id = :org_id"), {"org_id": org_id}).first()
    return bool(row and row.is_active)


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

    if row is None or not row.is_active or not _org_login_ok(db, row.role, row.org_id):
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
