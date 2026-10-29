"""Réglages : choix du CRM et de la base Notion (C05, C06, C09)."""

import httpx
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.crm_settings import InvalidCrmChoice, choose_crm, crm_screen
from prospection.domain.crm_choice import Crm
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import get_box, get_engine, get_http_client, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/reglages", dependencies=[Depends(require_session)])


def _page(
    request: Request,
    engine: Engine,
    box: SecretBox,
    client: httpx.Client,
    error: str | None = None,
    status_code: int = 200,
) -> Response:
    context = {"tab": "settings", "screen": crm_screen(engine, box, client), "error": error}
    return templates.TemplateResponse(
        request, "reglages_crm.html", context, status_code=status_code
    )


@router.get("/crm", response_class=HTMLResponse)
def crm_page(
    request: Request,
    engine: Engine = Depends(get_engine),  # noqa: B008
    box: SecretBox = Depends(get_box),  # noqa: B008
    client: httpx.Client = Depends(get_http_client),  # noqa: B008
) -> Response:
    return _page(request, engine, box, client)


@router.post("/crm")
def save_crm_choice(
    request: Request,
    crm: str = Form("none"),
    base: str = Form(""),
    engine: Engine = Depends(get_engine),  # noqa: B008
    box: SecretBox = Depends(get_box),  # noqa: B008
    client: httpx.Client = Depends(get_http_client),  # noqa: B008
) -> Response:
    choice = Crm.NOTION if crm == Crm.NOTION.value else Crm.NONE
    try:
        choose_crm(engine, box, client, choice, base)
    except InvalidCrmChoice as error:
        return _page(request, engine, box, client, str(error), 400)
    return RedirectResponse("/reglages/crm", status_code=303)
