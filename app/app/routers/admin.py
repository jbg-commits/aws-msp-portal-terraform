from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_engineer
from app.auth.security import generate_temp_password, hash_password
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/organizations", response_class=HTMLResponse)
def list_organizations(
    request: Request,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    orgs = db.execute(select(Organization).order_by(Organization.name)).scalars().all()
    return templates.TemplateResponse(request, "admin/organizations.html", {"user": user, "orgs": orgs})


@router.get("/admin/organizations/new", response_class=HTMLResponse)
def new_organization_form(
    request: Request,
    user: CurrentUser = Depends(require_engineer),
):
    return templates.TemplateResponse(request, "admin/new_organization.html", {"user": user, "error": None})


@router.post("/admin/organizations", response_class=HTMLResponse)
def create_organization(
    request: Request,
    org_name: str = Form(...),
    client_email: str = Form(...),
    client_full_name: str = Form(...),
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    existing = db.execute(
        text("SELECT 1 FROM users WHERE lower(email) = lower(:email)"), {"email": client_email}
    ).first()
    if existing:
        return templates.TemplateResponse(
            request,
            "admin/new_organization.html",
            {"user": user, "error": f"A user with email {client_email} already exists."},
            status_code=400,
        )

    org = Organization(name=org_name.strip())
    db.add(org)
    db.flush()  # assigns org.id within this transaction

    temp_password = generate_temp_password()
    client = User(
        org_id=org.id,
        role="client",
        email=client_email.strip().lower(),
        password_hash=hash_password(temp_password),
        full_name=client_full_name.strip(),
    )
    db.add(client)
    db.flush()

    return templates.TemplateResponse(
        request,
        "admin/new_organization.html",
        {
            "user": user,
            "error": None,
            "created": {"org_name": org.name, "client_email": client.email, "temp_password": temp_password},
        },
    )


@router.get("/admin/organizations/{org_id}/users/new", response_class=HTMLResponse)
def new_client_user_form(
    request: Request,
    org_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request, "admin/new_client_user.html", {"user": user, "org": org, "error": None}
    )


@router.post("/admin/organizations/{org_id}/users", response_class=HTMLResponse)
def create_client_user(
    request: Request,
    org_id: int,
    email: str = Form(...),
    full_name: str = Form(...),
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404)

    existing = db.execute(
        text("SELECT 1 FROM users WHERE lower(email) = lower(:email)"), {"email": email}
    ).first()
    if existing:
        return templates.TemplateResponse(
            request,
            "admin/new_client_user.html",
            {"user": user, "org": org, "error": f"A user with email {email} already exists."},
            status_code=400,
        )

    temp_password = generate_temp_password()
    client = User(
        org_id=org.id,
        role="client",
        email=email.strip().lower(),
        password_hash=hash_password(temp_password),
        full_name=full_name.strip(),
    )
    db.add(client)
    db.flush()

    return templates.TemplateResponse(
        request,
        "admin/new_client_user.html",
        {
            "user": user,
            "org": org,
            "error": None,
            "created": {"client_email": client.email, "temp_password": temp_password},
        },
    )
