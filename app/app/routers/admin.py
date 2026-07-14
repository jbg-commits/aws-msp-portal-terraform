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


def _reset_user_password(db: Session, target: User) -> str:
    """Generates a new temp password for an existing user, replacing the
    email-based "forgot password" flow this app deliberately doesn't have
    (no outbound email capability exists). Mirrors create_organization's/
    create_client_user's shown-once pattern.
    """
    temp_password = generate_temp_password()
    target.password_hash = hash_password(temp_password)
    db.flush()
    return temp_password


@router.get("/admin/organizations/{org_id}", response_class=HTMLResponse)
def organization_detail(
    request: Request,
    org_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404)
    users = db.execute(
        select(User).where(User.org_id == org_id, User.role == "client").order_by(User.full_name)
    ).scalars().all()
    return templates.TemplateResponse(
        request, "admin/organization_detail.html", {"user": user, "org": org, "users": users, "created": None}
    )


@router.post("/admin/organizations/{org_id}/deactivate")
def deactivate_organization(
    org_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404)
    org.is_active = False
    return RedirectResponse(f"/admin/organizations/{org_id}", status_code=303)


@router.post("/admin/organizations/{org_id}/reactivate")
def reactivate_organization(
    org_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404)
    org.is_active = True
    return RedirectResponse(f"/admin/organizations/{org_id}", status_code=303)


@router.post("/admin/organizations/{org_id}/users/{user_id}/reset-password", response_class=HTMLResponse)
def reset_client_password(
    request: Request,
    org_id: int,
    user_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404)

    # users carries no RLS (see 0001_initial_schema.py -- login chicken-and-
    # egg), so db.get(User, user_id) alone would return ANY user regardless
    # of org. This explicit check is what actually enforces the org
    # boundary here -- it's the one spot in this feature that isn't
    # protected by RLS for free the way tickets/organizations are.
    target = db.get(User, user_id)
    if target is None or target.org_id != org_id or target.role != "client":
        raise HTTPException(status_code=404)

    temp_password = _reset_user_password(db, target)
    users = db.execute(
        select(User).where(User.org_id == org_id, User.role == "client").order_by(User.full_name)
    ).scalars().all()
    return templates.TemplateResponse(
        request,
        "admin/organization_detail.html",
        {
            "user": user,
            "org": org,
            "users": users,
            "created": {"client_email": target.email, "temp_password": temp_password},
        },
    )


@router.get("/admin/engineers", response_class=HTMLResponse)
def list_engineers(
    request: Request,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    engineers = db.execute(select(User).where(User.role == "engineer").order_by(User.full_name)).scalars().all()
    return templates.TemplateResponse(
        request, "admin/engineers.html", {"user": user, "engineers": engineers, "created": None}
    )


@router.get("/admin/engineers/new", response_class=HTMLResponse)
def new_engineer_form(
    request: Request,
    user: CurrentUser = Depends(require_engineer),
):
    return templates.TemplateResponse(request, "admin/new_engineer.html", {"user": user, "error": None})


@router.post("/admin/engineers", response_class=HTMLResponse)
def create_engineer(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    existing = db.execute(
        text("SELECT 1 FROM users WHERE lower(email) = lower(:email)"), {"email": email}
    ).first()
    if existing:
        return templates.TemplateResponse(
            request,
            "admin/new_engineer.html",
            {"user": user, "error": f"A user with email {email} already exists."},
            status_code=400,
        )

    temp_password = generate_temp_password()
    engineer = User(
        org_id=None,
        role="engineer",
        email=email.strip().lower(),
        password_hash=hash_password(temp_password),
        full_name=full_name.strip(),
    )
    db.add(engineer)
    db.flush()

    return templates.TemplateResponse(
        request,
        "admin/new_engineer.html",
        {
            "user": user,
            "error": None,
            "created": {"email": engineer.email, "temp_password": temp_password},
        },
    )


@router.post("/admin/engineers/{user_id}/reset-password", response_class=HTMLResponse)
def reset_engineer_password(
    request: Request,
    user_id: int,
    user: CurrentUser = Depends(require_engineer),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None or target.role != "engineer":
        raise HTTPException(status_code=404)

    temp_password = _reset_user_password(db, target)
    engineers = db.execute(select(User).where(User.role == "engineer").order_by(User.full_name)).scalars().all()
    return templates.TemplateResponse(
        request,
        "admin/engineers.html",
        {
            "user": user,
            "engineers": engineers,
            "created": {"email": target.email, "temp_password": temp_password},
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
