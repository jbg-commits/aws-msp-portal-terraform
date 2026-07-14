from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import Forbidden, NotAuthenticated
from app.routers import account, admin, auth, dashboard, tickets

app = FastAPI(title="Hive")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.exception_handler(NotAuthenticated)
def handle_not_authenticated(request: Request, exc: NotAuthenticated):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(Forbidden)
def handle_forbidden(request: Request, exc: Forbidden):
    return templates.TemplateResponse(request, "403.html", {}, status_code=403)


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    # Deliberately static and DB-free: this is the ALB target group health
    # check path (matcher = 200 in modules/compute/main.tf), which gates
    # CodeDeploy's alarm-based auto-rollback. A DB round-trip here would
    # turn a transient RDS blip into a rollback unrelated to app code.
    return templates.TemplateResponse(request, "landing.html", {})


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(tickets.router)
app.include_router(admin.router)
app.include_router(account.router)
