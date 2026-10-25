"""Pages de connexion et de déconnexion (C01, C82)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.login import LoginOutcome, attempt_login
from prospection.config import Settings
from prospection.ui.client_ip import client_ip
from prospection.ui.cookies import set_session_cookie
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.session import COOKIE_NAME, make_session_value

router = APIRouter()


def safe_destination(suite: str) -> str:
    """N'accepte qu'un chemin relatif de l'app (pas de redirection ouverte)."""
    if suite.startswith("/") and not suite.startswith("//") and "\\" not in suite:
        return suite
    return "/"


@router.get("/connexion", response_class=HTMLResponse)
def login_page(request: Request, suite: str = "/") -> Response:
    context = {"suite": safe_destination(suite), "error": None}
    return templates.TemplateResponse(request, "connexion.html", context)


@router.post("/connexion")
def login(
    request: Request,
    mot_de_passe: str = Form(""),
    suite: str = Form("/"),
    settings: Settings = Depends(get_settings),  # noqa: B008
    engine: Engine = Depends(get_engine),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:
    ip = client_ip(request, settings)
    password_hash = settings.app_password_hash.get_secret_value()
    with engine.begin() as conn:
        result = attempt_login(conn, password_hash, mot_de_passe, ip, now)
    destination = safe_destination(suite)
    if result.outcome is LoginOutcome.OK:
        response = RedirectResponse(destination, status_code=303)
        set_session_cookie(response, make_session_value(settings, now))
        return response
    if result.outcome is LoginOutcome.LOCKED:
        minutes = int(result.retry_after.total_seconds() // 60)
        error, status = f"Trop d'essais. Réessayez dans {minutes} min.", 429
    else:
        error, status = "Mot de passe incorrect.", 401
    context = {"suite": destination, "error": error}
    return templates.TemplateResponse(request, "connexion.html", context, status_code=status)


@router.post("/deconnexion")
def logout() -> Response:
    response = RedirectResponse("/connexion", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")
    return response
