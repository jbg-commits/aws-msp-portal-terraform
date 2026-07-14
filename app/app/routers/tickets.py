from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_engineer
from app.db.session import get_db
from app.models.organization import Organization
from app.models.remote_session import RemoteSession
from app.models.ticket import PRIORITIES, STATUSES, Ticket
from app.models.ticket_comment import TicketComment
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _finalize_remote_sessions(db: Session, ticket_id: int) -> None:
    """Lazily closes out any remote session on this ticket whose 30-second
    reconnect grace period has actually elapsed.

    A single atomic, idempotent UPDATE -- safe to call unconditionally on
    every request that touches remote sessions for this ticket, the same
    lazy-on-next-request idiom _next_display_id uses instead of a cron job.
    ended_at is fixed at disconnect+30s exactly once here, rather than ever
    being computed fresh at read time, so the billable boundary doesn't
    drift depending on when someone happens to look at the page.
    """
    db.execute(
        text(
            """
            UPDATE remote_sessions
            SET ended_at = disconnected_at + interval '30 seconds'
            WHERE ticket_id = :ticket_id
              AND ended_at IS NULL
              AND disconnected_at IS NOT NULL
              AND now() - disconnected_at >= interval '30 seconds'
            """
        ),
        {"ticket_id": ticket_id},
    )


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
    deleted: bool = False,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Ticket, Organization.name).join(Organization, Organization.id == Ticket.org_id)

    # Never trust the raw query param for a Client -- the trash view is
    # Engineer-only, same discipline as org_id/status below.
    show_deleted = deleted and user.is_engineer
    query = query.where(Ticket.deleted_at.is_not(None)) if show_deleted else query.where(Ticket.deleted_at.is_(None))

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
        {
            "user": user,
            "tickets": rows,
            "orgs": orgs,
            "statuses": STATUSES,
            "filter_org_id": org_id,
            "filter_status": status,
            "show_deleted": show_deleted,
        },
    )


@router.get("/tickets/new", response_class=HTMLResponse)
def new_ticket_form(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orgs = (
        db.execute(select(Organization).where(Organization.is_active.is_(True)).order_by(Organization.name))
        .scalars()
        .all()
        if user.is_engineer
        else []
    )
    return templates.TemplateResponse(request, "tickets/new.html", {"user": user, "orgs": orgs, "error": None})


@router.post("/tickets", response_class=HTMLResponse)
def create_ticket(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    org_id: int | None = Form(None),
    system_summary: str | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # org_id is never trusted from client-submitted form data for a Client
    # user -- always forced to their own org server-side. An Engineer must
    # explicitly pick a target org.
    if user.is_engineer:
        if org_id is None:
            orgs = db.execute(
                select(Organization).where(Organization.is_active.is_(True)).order_by(Organization.name)
            ).scalars().all()
            return templates.TemplateResponse(
                request, "tickets/new.html", {"user": user, "orgs": orgs, "error": "Select an organization."}, status_code=400
            )
        # Defensive re-check, same "never trust a client-submitted value
        # blindly" discipline as system_summary below -- a stale page could
        # still submit a since-deactivated org_id.
        org = db.get(Organization, org_id)
        if org is None or not org.is_active:
            orgs = db.execute(
                select(Organization).where(Organization.is_active.is_(True)).order_by(Organization.name)
            ).scalars().all()
            return templates.TemplateResponse(
                request, "tickets/new.html", {"user": user, "orgs": orgs, "error": "Select an organization."}, status_code=400
            )
        target_org_id = org_id
    else:
        target_org_id = user.org_id

    # Never trust this blindly -- a malformed/tampered value should degrade
    # to "no summary" rather than block ticket creation. Absent entirely for
    # tickets created from a plain browser (window.hiveDesktop doesn't exist
    # there, so the hidden field is never populated).
    parsed_summary = None
    if system_summary:
        try:
            candidate = json.loads(system_summary)
            parsed_summary = candidate if isinstance(candidate, dict) else None
        except (json.JSONDecodeError, TypeError):
            parsed_summary = None

    ticket = Ticket(
        org_id=target_org_id,
        display_id=_next_display_id(db),
        title=title.strip(),
        description=description.strip(),
        created_by=user.id,
        system_summary=parsed_summary,
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

    # Soft-deleted tickets aren't RLS-protected (deleted_at isn't an org
    # boundary) -- this is an app-layer rule, not a tenancy one. A Client
    # gets the same 404 as a genuinely nonexistent ticket; an Engineer can
    # still open it to restore it.
    if ticket.deleted_at is not None and not user.is_engineer:
        raise HTTPException(status_code=404)

    _finalize_remote_sessions(db, ticket_id)

    org = db.get(Organization, ticket.org_id)
    comments = db.execute(
        select(TicketComment, User.full_name)
        .join(User, User.id == TicketComment.author_id)
        .where(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
    ).all()
    engineers = db.execute(select(User).where(User.role == "engineer")).scalars().all() if user.is_engineer else []

    remote_sessions = db.execute(
        select(RemoteSession, User.full_name)
        .join(User, User.id == RemoteSession.engineer_id)
        .where(RemoteSession.ticket_id == ticket_id)
        .order_by(RemoteSession.started_at.desc())
    ).all()

    current_session, session_history = None, remote_sessions
    if remote_sessions:
        top_session, _ = remote_sessions[0]
        if top_session.ended_at is None or top_session.summary is None:
            current_session = remote_sessions[0]
            session_history = remote_sessions[1:]

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
            "current_session": current_session,
            "session_history": session_history,
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


@router.post("/tickets/{ticket_id}/delete")
def delete_ticket(
    ticket_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)

    # Idempotent -- a double-click just no-ops on the second attempt since
    # deleted_at is no longer NULL.
    db.execute(
        text("UPDATE tickets SET deleted_at = now() WHERE id = :id AND deleted_at IS NULL"),
        {"id": ticket_id},
    )

    return RedirectResponse("/tickets", status_code=303)


@router.post("/tickets/{ticket_id}/restore")
def restore_ticket(
    ticket_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)

    db.execute(
        text("UPDATE tickets SET deleted_at = NULL WHERE id = :id AND deleted_at IS NOT NULL"),
        {"id": ticket_id},
    )

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/remote-sessions/start")
def start_remote_session(
    ticket_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    # Hive does not detect the actual remote-support connection itself (that
    # happens in whatever external tool -- GoToAssist, Datto RMM, etc. -- the
    # Engineer is already using); this only records what the Engineer tells
    # it via this click.
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)

    _finalize_remote_sessions(db, ticket_id)

    # Resume within the 30s grace window if one exists -- same continuous
    # billable session, not a new one.
    resumed = db.execute(
        text(
            """
            UPDATE remote_sessions SET disconnected_at = NULL
            WHERE ticket_id = :ticket_id AND ended_at IS NULL AND disconnected_at IS NOT NULL
            RETURNING id
            """
        ),
        {"ticket_id": ticket_id},
    ).first()

    if resumed is None:
        # No open/resumable session -- start a new one. The partial unique
        # index (one open session per ticket) makes this atomic against a
        # concurrent double-click with zero row locking, same idiom as
        # _next_display_id's INSERT ... ON CONFLICT.
        db.execute(
            text(
                """
                INSERT INTO remote_sessions (ticket_id, engineer_id)
                VALUES (:ticket_id, :engineer_id)
                ON CONFLICT (ticket_id) WHERE ended_at IS NULL DO NOTHING
                """
            ),
            {"ticket_id": ticket_id, "engineer_id": user.id},
        )

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/remote-sessions/end")
def end_remote_session(
    ticket_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)

    # Idempotent -- a double-click just no-ops on the second attempt since
    # disconnected_at is no longer NULL.
    db.execute(
        text(
            """
            UPDATE remote_sessions SET disconnected_at = now()
            WHERE ticket_id = :ticket_id AND ended_at IS NULL AND disconnected_at IS NULL
            """
        ),
        {"ticket_id": ticket_id},
    )

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@router.post("/tickets/{ticket_id}/remote-sessions/{session_id}/summary")
def submit_remote_session_summary(
    ticket_id: int,
    session_id: int,
    summary: str = Form(...),
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404)

    _finalize_remote_sessions(db, ticket_id)

    session = db.get(RemoteSession, session_id)
    if session is None or session.ticket_id != ticket_id:
        raise HTTPException(status_code=404)

    # Server-side enforcement, not just a hidden UI element -- a session
    # can only be summarized once it's actually finalized.
    if session.ended_at is None:
        raise HTTPException(status_code=400, detail="Session not finalized yet")

    session.summary = summary.strip()

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
