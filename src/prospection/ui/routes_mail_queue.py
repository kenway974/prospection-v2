"""Page « Envois » : file du mail d'audit, annulation, reprise ; plafond par jour réglé dans
Réglages → Mail (C169, C170). Afficher et déléguer, aucune règle ici."""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.mail_queue_view import (
    InvalidLimit,
    cancel_line,
    change_limit,
    queue_screen,
    resume,
)
from prospection.config import Settings
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])
ENGINE, NOW, SETTINGS = Depends(get_engine), Depends(get_now), Depends(get_settings)
PAGE = "/prospects/envois"


@router.get(PAGE, response_class=HTMLResponse)
def queue_page(
    request: Request, engine: Engine = ENGINE, now: datetime = NOW, settings: Settings = SETTINGS
) -> Response:
    screen = queue_screen(engine, now, settings.timezone)
    return templates.TemplateResponse(request, "envois.html", {"tab": "prospects", "s": screen})


@router.post(PAGE + "/{queue_id}/annuler")
def cancel(queue_id: int, engine: Engine = ENGINE, now: datetime = NOW) -> Response:
    cancel_line(engine, queue_id, now)
    return RedirectResponse(PAGE, status_code=303)


@router.post(PAGE + "/reprendre")
def restart(engine: Engine = ENGINE) -> Response:
    resume(engine)
    return RedirectResponse(PAGE, status_code=303)


@router.post("/reglages/mail/plafond")
def save_limit(
    request: Request, plafond: str = Form("", max_length=5), engine: Engine = ENGINE
) -> Response:
    try:
        change_limit(engine, plafond)
    except InvalidLimit as error:
        context = {"tab": "settings", "message": str(error), "back": "/reglages/mail"}
        return templates.TemplateResponse(request, "erreur.html", context, status_code=400)
    return RedirectResponse("/reglages/mail", status_code=303)
