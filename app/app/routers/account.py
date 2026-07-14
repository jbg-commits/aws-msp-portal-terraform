from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.security import MIN_PASSWORD_LENGTH, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/account", response_class=HTMLResponse)
def account_form(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    return templates.TemplateResponse(request, "account.html", {"user": user, "error": None, "success": None})


@router.post("/account/password", response_class=HTMLResponse)
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = db.get(User, user.id)

    if not verify_password(current_password, target.password_hash):
        error = "Current password is incorrect."
    elif new_password != confirm_password:
        error = "New password and confirmation don't match."
    elif len(new_password) < MIN_PASSWORD_LENGTH:
        error = f"New password must be at least {MIN_PASSWORD_LENGTH} characters."
    else:
        error = None

    if error:
        return templates.TemplateResponse(
            request, "account.html", {"user": user, "error": error, "success": None}, status_code=400
        )

    target.password_hash = hash_password(new_password)

    return templates.TemplateResponse(
        request, "account.html", {"user": user, "error": None, "success": "Password changed."}
    )
