from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# pool_pre_ping + pool_recycle matter specifically because this environment's
# RDS instance is stopped nightly/weekends by an EventBridge Scheduler --
# without pre_ping, the first request after a restart would hit a dead pooled
# connection instead of transparently reconnecting.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Per-request DB session, wrapped in a single transaction that commits
    on success / rolls back on any exception.

    This does NOT set any Row-Level Security context -- that happens in
    auth.dependencies.get_current_user, which itself depends on this same
    function. FastAPI caches dependency results per request, so any route
    handler that also declares `db: Session = Depends(get_db)` receives the
    IDENTICAL Session instance get_current_user already scoped -- not a
    fresh one. That sharing is what makes the RLS context actually apply to
    the queries a route handler issues.
    """
    db = SessionLocal()
    try:
        with db.begin():
            yield db
    finally:
        db.close()
