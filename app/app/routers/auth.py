from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import SESSION_COOKIE_NAME, CurrentUser, get_current_user
from app.auth.security import generate_session_token, verify_password
from app.config import get_settings
from app.db.session import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # No RLS context exists yet -- correct, since users/sessions carry no RLS
    # policies (see 0001_initial_schema.py). Generic error message on any
    # failure so we never reveal whether the email exists.
    row = db.execute(
        text(
            "SELECT id, password_hash, is_active FROM users WHERE lower(email) = lower(:email)"
        ),
        {"email": email},
    ).first()

    if row is None or not row.is_active or not verify_password(password, row.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid email or password."}, status_code=401
        )

    user_row = db.execute(
        text("SELECT role, org_id FROM users WHERE id = :id"), {"id": row.id}
    ).first()

    token = generate_session_token()
    db.execute(
        text(
            """
            INSERT INTO sessions (token, user_id, role, org_id, expires_at)
            VALUES (:token, :user_id, :role, :org_id, now() + interval '8 hours')
            """
        ),
        {"token": token, "user_id": row.id, "role": user_row.role, "org_id": user_row.org_id},
    )

    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=8 * 3600,
    )
    return response


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        db.execute(
            text("UPDATE sessions SET revoked_at = now() WHERE token = :token"),
            {"token": token},
        )
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
