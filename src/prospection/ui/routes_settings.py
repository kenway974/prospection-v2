"""Réglages : clés API (C02, C04)."""

from dataclasses import dataclass
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.api_keys import (
    EmptyKey,
    InvalidKey,
    KeyStatus,
    key_statuses,
    remove_key,
    store_key,
)
from prospection.application.key_tests import run_key_test
from prospection.config import Settings
from prospection.domain.services import Service
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import (
    get_box,
    get_engine,
    get_http_client,
    get_now,
    get_settings,
    templates,
)
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
    return templates.TemplateResponse(request, "reglages.html", {"tab": "settings"})


@dataclass(frozen=True)
class KeyView:
    status: KeyStatus
    saved_on: str | None


def key_views(engine: Engine, box: SecretBox, settings: Settings) -> list[KeyView]:
    return [
        KeyView(status, short_date(status.saved_at, settings.timezone) if status.saved_at else None)
        for status in key_statuses(engine, box)
    ]


def keys_page(
    request: Request,
    engine: Engine,
    box: SecretBox,
    settings: Settings,
    error: dict[str, object] | None = None,
    status_code: int = 200,
) -> Response:
    keys = key_views(engine, box, settings)
    context = {"tab": "settings", "keys": keys, "error": error}
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
        message = "Collez la clé avant d'enregistrer."
    except InvalidKey:
        message = "Clé invalide : recopiez-la depuis le site du service, sans caractère spécial."
    else:
        return RedirectResponse("/reglages/cles", status_code=303)
    error = {"service": service, "message": message}
    return keys_page(request, engine, box, settings, error=error, status_code=400)
    return RedirectResponse("/reglages/cles", status_code=303)


@router.post("/cles/{name}/supprimer")
def remove(
    request: Request,
    name: str,
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:
    remove_key(engine, service_from(name))
    if request.headers.get("hx-request") == "true":
        # Suppression confirmée via HTMX : la page se recharge entièrement.
        return Response(status_code=200, headers={"HX-Redirect": "/reglages/cles"})
    return RedirectResponse("/reglages/cles", status_code=303)


@router.post("/cles/{name}/tester")
def test_key(
    request: Request,
    name: str,
    engine: Engine = Depends(get_engine),  # noqa: B008
    box: SecretBox = Depends(get_box),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    client: httpx.Client = Depends(get_http_client),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:
    service = service_from(name)
    run_key_test(engine, box, service, client, now)
    if request.headers.get("hx-request") != "true":
        return RedirectResponse("/reglages/cles", status_code=303)
    key = next(k for k in key_views(engine, box, settings) if k.status.service is service)
    return templates.TemplateResponse(request, "_cle.html", {"key": key, "error": None})
