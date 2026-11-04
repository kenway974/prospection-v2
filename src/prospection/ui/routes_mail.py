"""Mail d'audit d'un prospect : relecture puis envoi depuis Gmail (C145 à C147)."""

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.audit_mail import MailBlocked, mail_screen, send_audit_mail
from prospection.application.prospect_card import UnknownProspect
from prospection.config import Settings
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import (
    get_box,
    get_engine,
    get_http_client,
    get_now,
    get_settings,
    templates,
)
from prospection.ui.formatting import short_datetime
from prospection.ui.session import require_session

router = APIRouter(prefix="/prospects", dependencies=[Depends(require_session)])
ENGINE, SETTINGS, BOX = Depends(get_engine), Depends(get_settings), Depends(get_box)
CLIENT, NOW = Depends(get_http_client), Depends(get_now)


def _page(
    request: Request, engine: Engine, box: SecretBox, client: httpx.Client, settings: Settings,
    prospect_id: int, now: datetime, typed: dict[str, str] | None = None,
    error: str | None = None, code: int = 200,
) -> Response:  # fmt: skip
    try:
        screen = mail_screen(engine, box, client, settings.gmail_oauth(), settings.public_base(),
                             prospect_id, now)  # fmt: skip
    except UnknownProspect:
        raise HTTPException(status_code=404) from None
    draft = screen.draft
    values = typed or {
        "a": screen.recipients[0] if screen.recipients else "",
        "objet": draft.subject if draft else "", "texte": draft.body if draft else "",
    }  # fmt: skip
    sent = short_datetime(screen.sent_on, settings.timezone) if screen.sent_on else None
    context = {"tab": "prospects", "screen": screen, "values": values, "error": error,
               "sent": sent}  # fmt: skip
    return templates.TemplateResponse(request, "mail.html", context, status_code=code)


@router.get("/{prospect_id}/mail", response_class=HTMLResponse)
def mail_page(
    request: Request, prospect_id: int, engine: Engine = ENGINE, box: SecretBox = BOX,
    client: httpx.Client = CLIENT, settings: Settings = SETTINGS, now: datetime = NOW,
) -> Response:  # fmt: skip
    return _page(request, engine, box, client, settings, prospect_id, now)


@router.post("/{prospect_id}/mail")
def send_mail(
    request: Request, prospect_id: int, a: str = Form("", max_length=320),
    objet: str = Form("", max_length=1000), texte: str = Form("", max_length=40_000),
    engine: Engine = ENGINE, box: SecretBox = BOX, client: httpx.Client = CLIENT,
    settings: Settings = SETTINGS, now: datetime = NOW,
) -> Response:  # fmt: skip
    try:
        send_audit_mail(engine, box, client, settings.gmail_oauth(), settings.public_base(),
                        prospect_id, a, objet, texte, now, settings.timezone)  # fmt: skip
    except UnknownProspect:
        raise HTTPException(status_code=404) from None
    except MailBlocked as blocked:
        typed = {"a": a, "objet": objet, "texte": texte}
        return _page(request, engine, box, client, settings, prospect_id, now, typed,
                     str(blocked), 400)  # fmt: skip
    return RedirectResponse(f"/prospects/{prospect_id}", status_code=303)
