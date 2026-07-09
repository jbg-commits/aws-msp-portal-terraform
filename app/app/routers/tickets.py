from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_engineer
from app.db.session import get_db
from app.models.organization import Organization
from app.models.ticket import PRIORITIES, STATUSES, Ticket
from app.models.ticket_comment import TicketComment
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _next_display_id(db: Session) -> str:
    """Atomically claims the next T[YYMMDD].[N] number for today, where N
    resets to 1 each day and is shared globally across all organizations.

    INSERT ... ON CONFLICT DO UPDATE is a single atomic statement -- Postgres
    serializes concurrent claims for the same day at the row level, so two
    tickets created in the same instant can never get the same number
    without any application-level locking.
    """
    row = db.execute(
        text(
            """
            INSERT INTO daily_ticket_sequences (day, last_sequence)
            VALUES (CURRENT_DATE, 1)
            ON CONFLICT (day) DO UPDATE SET last_sequence = daily_ticket_sequences.last_sequence + 1
            RETURNING day, last_sequence
            """
        )
    ).one()
    return f"T{row.day.strftime('%y%m%d')}.{row.last_sequence}"


@router.get("/tickets", response_class=HTMLResponse)
def list_tickets(
    request: Request,
    org_id: int | None = None,
    status: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Ticket, Organization.name).join(Organization, Organization.id == Ticket.org_id)

    if user.is_engineer:
        if org_id is not None:
            query = query.where(Ticket.org_id == org_id)
        if status is not None:
            query = query.where(Ticket.status == status)
    else:
        # Belt-and-suspenders: RLS already restricts this, but never rely on
        # that alone at the query layer.
        query = query.where(Ticket.org_id == user.org_id)

    query = query.order_by(Ticket.created_at.desc())
    rows = db.execute(query).all()

    orgs = db.execute(select(Organization).order_by(Organization.name)).scalars().all() if user.is_engineer else []

    return templates.TemplateResponse(
        request,
        "tickets/list.html",
        {"user": user, "tickets": rows, "orgs": orgs, "statuses": STATUSES, "filter_org_id": org_id, "filter_status": status},
    )


@router.get("/tickets/new", response_class=HTMLResponse)
def new_ticket_form(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orgs = db.execute(select(Organization).order_by(Organization.name)).scalars().all() if user.is_engineer else []
    return templates.TemplateResponse(request, "tickets/new.html", {"user": user, "orgs": orgs, "error": None})


@router.post("/tickets", response_class=HTMLResponse)
def create_ticket(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    org_id: int | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # org_id is never trusted from client-submitted form data for a Client
    # user -- always forced to their own org server-side. An Engineer must
    # explicitly pick a target org.
    if user.is_engineer:
        if org_id is None:
            orgs = db.execute(select(Organization).order_by(Organization.name)).scalars().all()
            return templates.TemplateResponse(
                request, "tickets/new.html", {"user": user, "orgs": orgs, "error": "Select an organization."}, status_code=400
            )
        target_org_id = org_id
    else:
        target_org_id = user.org_id

    ticket = Ticket(
        org_id=target_org_id,
        display_id=_next_display_id(db),
        title=title.strip(),
        description=description.strip(),
        created_by=user.id,
    )
    db.add(ticket)
    db.flush()

    return RedirectResponse(f"/tickets/{ticket.id}", status_code=303)


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(
    request: Request,
    ticket_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # For a Client, RLS already makes a cross-org ticket_id simply not exist
    # in this query's result set -- so a plain 404 here, with no extra
    # org-comparison code, is both correct and leak-free (indistinguishable
    # from a genuinely nonexistent id).
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)

    org = db.get(Organization, ticket.org_id)
    comments = db.execute(
        select(TicketComment, User.full_name)
        .join(User, User.id == TicketComment.author_id)
        .where(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
    ).all()
    engineers = db.execute(select(User).where(User.role == "engineer")).scalars().all() if user.is_engineer else []

    return templates.TemplateResponse(
        request,
        "tickets/detail.html",
        {
            "user": user,
            "ticket": ticket,
            "org": org,
            "comments": comments,
            "engineers": engineers,
            "statuses": STATUSES,
            "priorities": PRIORITIES,
        },
    )


@router.post("/tickets/{ticket_id}/comments")
def add_comment(
    ticket_id: int,
    body: str = Form(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Same 404-before-write pattern as ticket_detail: check visibility via a
    # SELECT before attempting the INSERT, rather than letting RLS's WITH
    # CHECK reject an insert into an invisible ticket (which would surface
    # as a raw DB error, not a clean 404).
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)

    comment = TicketComment(
        ticket_id=ticket_id,
        org_id=ticket.org_id,
        author_id=user.id,
        body=body.strip(),
    )
    db.add(comment)

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status: str = Form(...),
    priority: str = Form(...),
    assigned_engineer_id: str = Form(""),
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)
    if status not in STATUSES or priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="invalid status or priority")

    ticket.status = status
    ticket.priority = priority
    ticket.assigned_engineer_id = int(assigned_engineer_id) if assigned_engineer_id else None

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
