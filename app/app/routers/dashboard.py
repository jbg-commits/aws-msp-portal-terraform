from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.organization import Organization
from app.models.ticket import Ticket

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.is_engineer:
        # RLS already scopes this to "all rows" for an engineer; the org join
        # is purely for display (counts broken out per org).
        rows = db.execute(
            select(Organization.name, Ticket.status, func.count())
            .join(Ticket, Ticket.org_id == Organization.id, isouter=True)
            .group_by(Organization.name, Ticket.status)
        ).all()
        by_org: dict[str, dict[str, int]] = {}
        for org_name, status, count in rows:
            by_org.setdefault(org_name, {})[status or "—"] = count
        return templates.TemplateResponse(
            request, "dashboard.html", {"user": user, "by_org": by_org}
        )

    # Client: belt-and-suspenders explicit org filter on top of RLS.
    rows = db.execute(
        select(Ticket.status, func.count())
        .where(Ticket.org_id == user.org_id)
        .group_by(Ticket.status)
    ).all()
    counts = {status: count for status, count in rows}
    return templates.TemplateResponse(request, "dashboard.html", {"user": user, "counts": counts})
