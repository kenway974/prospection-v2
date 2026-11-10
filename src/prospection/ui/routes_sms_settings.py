"""Réglages → SMS (C175) : afficher et déléguer, aucune règle ici."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.sms_settings_screen import change_sms_settings, sms_settings_screen
from prospection.domain.sms_settings import InvalidSmsSettings
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import get_box, get_engine, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/reglages/sms", dependencies=[Depends(require_session)])
ENGINE, BOX = Depends(get_engine), Depends(get_box)


def _page(request: Request, engine: Engine, box: SecretBox, code: int = 200,
          errors: dict[str, str] | None = None, values: dict[str, str] | None = None
          ) -> Response:  # fmt: skip
    screen = sms_settings_screen(engine, box)
    shown = values or {"actifs": "on" if screen.settings.enabled else "",
                       "expediteur": screen.settings.sender,
                       "plafond": str(screen.settings.daily_limit)}  # fmt: skip
    context = {"tab": "settings", "values": shown, "errors": errors or {},
               "has_key": screen.has_key}  # fmt: skip
    return templates.TemplateResponse(request, "reglages_sms.html", context, status_code=code)


@router.get("", response_class=HTMLResponse)
def sms_page(request: Request, engine: Engine = ENGINE, box: SecretBox = BOX) -> Response:
    return _page(request, engine, box)


@router.post("")
def save_sms(
    request: Request, actifs: str = Form("", max_length=5),
    expediteur: str = Form("", max_length=40), plafond: str = Form("", max_length=5),
    engine: Engine = ENGINE, box: SecretBox = BOX,
) -> Response:  # fmt: skip
    try:
        change_sms_settings(engine, actifs, expediteur, plafond)
    except InvalidSmsSettings as error:
        values = {"actifs": actifs, "expediteur": expediteur, "plafond": plafond}
        return _page(request, engine, box, 400, error.errors, values)
    return RedirectResponse("/reglages/sms", status_code=303)
