"""Réglages : clés API (C02, C04)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.api_keys import EmptyKey, key_statuses, remove_key, store_key
from prospection.config import Settings
from prospection.domain.services import Service
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import get_box, get_engine, get_now, get_settings, templates
from prospection.ui.formatting import short_date
from prospection.ui.session import require_session

router = APIRouter(prefix="/reglages", dependencies=[Depends(require_session)])


def service_from(name: str) -> Service:
    try:
        return Service(name)
    except ValueError:
        raise HTTPException(status_code=404) from None


@router.get("", response_class=HTMLResponse)
def hub(request: Request) -> Response:
    return templates.TemplateResponse(request, "reglages.html", {"tab": ""})


def keys_page(
    request: Request, engine: Engine, box: SecretBox, settings: Settings, **extra: object
) -> Response:
    status_code = int(str(extra.pop("status_code", 200)))
    keys = [
        {
            "status": status,
            "saved_on": status.saved_at and short_date(status.saved_at, settings.timezone),
        }
        for status in key_statuses(engine, box)
    ]
    context = {"tab": "", "keys": keys, **extra}
    return templates.TemplateResponse(
        request, "reglages_cles.html", context, status_code=status_code
    )


@router.get("/cles", response_class=HTMLResponse)
def keys(
    request: Request,
    engine: Engine = Depends(get_engine),  # noqa: B008
    box: SecretBox = Depends(get_box),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:
    return keys_page(request, engine, box, settings)


@router.post("/cles/{name}")
def save(
    request: Request,
    name: str,
    cle: str = Form(""),
    engine: Engine = Depends(get_engine),  # noqa: B008
    box: SecretBox = Depends(get_box),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:
    service = service_from(name)
    try:
        store_key(engine, box, service, cle, now)
    except EmptyKey:
        error = {"service": service, "message": "Collez la clé avant d'enregistrer."}
        return keys_page(request, engine, box, settings, error=error, status_code=400)
    return RedirectResponse("/reglages/cles", status_code=303)


@router.post("/cles/{name}/supprimer")
def remove(name: str, engine: Engine = Depends(get_engine)) -> Response:  # noqa: B008
    remove_key(engine, service_from(name))
    return RedirectResponse("/reglages/cles", status_code=303)
