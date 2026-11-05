"""Réglages → Mail d'audit : expéditeur, liens, rappel, connexion Gmail (C144)."""

import secrets
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.mail_settings import (
    change_mail_settings,
    connected_address,
    disconnect_gmail,
    finish_gmail,
    load_settings_screen,
    start_gmail,
)
from prospection.config import Settings
from prospection.domain.mail_settings import InvalidMailSettings
from prospection.sources.gmail import GmailRefused, GmailRevoked, GmailUnavailable
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import (
    get_box,
    get_engine,
    get_http_client,
    get_now,
    get_settings,
    templates,
)
from prospection.ui.session import require_session

router = APIRouter(prefix="/reglages", dependencies=[Depends(require_session)])
STATE_COOKIE = "__Host-gmail-state"
ENGINE, SETTINGS = Depends(get_engine), Depends(get_settings)
FORGED = "Retour de Google non reconnu. Recommencez la connexion depuis cet écran."
DENIED = "L'accord n'a pas été donné sur la page Google : Gmail n'est pas relié."
FAILED = "Google n'a pas pu relier Gmail. Réessayez dans un instant."
NOT_REVOKED = ("Gmail est délié de l'app, mais Google n'a pas confirmé : retirez aussi l'accès "
               "sur myaccount.google.com/permissions.")  # fmt: skip


def _page(
    request: Request, engine: Engine, settings: Settings, code: int = 200,
    errors: dict[str, str] | None = None, values: dict[str, str] | None = None,
    gmail_error: str | None = None,
) -> Response:  # fmt: skip
    saved = load_settings_screen(engine)
    shown = values or {"nom": saved.sender_name or "", "telephone": saved.phone or "",
                       "portfolio": saved.portfolio or "", "calendly": saved.calendly or "",
                       "jours": str(saved.reminder_days)}  # fmt: skip
    context = {"tab": "settings", "values": shown, "errors": errors or {},
               "address": connected_address(engine), "gmail_error": gmail_error,
               "can_connect": bool(settings.gmail_oauth() and settings.public_base())}  # fmt: skip
    return templates.TemplateResponse(request, "reglages_mail.html", context, status_code=code)


@router.get("/mail", response_class=HTMLResponse)
def mail_settings_page(
    request: Request, engine: Engine = ENGINE, settings: Settings = SETTINGS
) -> Response:
    return _page(request, engine, settings)


@router.post("/mail")
def save_mail_settings(
    request: Request, nom: str = Form("", max_length=200), telephone: str = Form("", max_length=60),
    portfolio: str = Form("", max_length=600), calendly: str = Form("", max_length=600),
    jours: str = Form("", max_length=5), engine: Engine = ENGINE, settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    values = {"nom": nom, "telephone": telephone, "portfolio": portfolio, "calendly": calendly,
              "jours": jours}  # fmt: skip
    try:
        change_mail_settings(engine, nom, telephone, portfolio, calendly, jours)
    except InvalidMailSettings as error:
        return _page(request, engine, settings, 400, error.errors, values)
    return RedirectResponse("/reglages/mail", status_code=303)


@router.get("/gmail/connecter")
def connect_gmail(
    request: Request, engine: Engine = ENGINE, settings: Settings = SETTINGS
) -> Response:
    oauth, base = settings.gmail_oauth(), settings.public_base()
    if oauth is None or base is None:
        return _page(request, engine, settings, 400)
    url, state = start_gmail(oauth, base)
    response = RedirectResponse(url, status_code=303)
    response.set_cookie(STATE_COOKIE, state, max_age=600, path="/", secure=True, httponly=True,
                        samesite="lax")  # fmt: skip
    return response


@router.get("/gmail/retour")
def gmail_back(
    request: Request, state: str = "", code: str = "", error: str = "",
    engine: Engine = ENGINE, settings: Settings = SETTINGS,
    box: SecretBox = Depends(get_box), client: httpx.Client = Depends(get_http_client),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    expected = request.cookies.get(STATE_COOKIE, "")
    oauth, base = settings.gmail_oauth(), settings.public_base()
    problem = None
    if not expected or not secrets.compare_digest(expected, state[:100]) or not oauth or not base:
        problem = FORGED
    elif error or not code:
        problem = DENIED
    else:
        try:
            finish_gmail(engine, box, client, oauth, base, code[:2000], now)
        except (GmailRefused, GmailRevoked, GmailUnavailable):
            problem = FAILED
    response = (_page(request, engine, settings, 400, gmail_error=problem) if problem
                else RedirectResponse("/reglages/mail", status_code=303))  # fmt: skip
    response.delete_cookie(STATE_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@router.post("/gmail/deconnecter")
def gmail_disconnect(
    request: Request, engine: Engine = ENGINE, settings: Settings = SETTINGS,
    box: SecretBox = Depends(get_box), client: httpx.Client = Depends(get_http_client),  # noqa: B008
) -> Response:  # fmt: skip
    if disconnect_gmail(engine, box, client):
        return RedirectResponse("/reglages/mail", status_code=303)
    return _page(request, engine, settings, gmail_error=NOT_REVOKED)
