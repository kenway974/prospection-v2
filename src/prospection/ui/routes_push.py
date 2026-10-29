"""Abonnement du téléphone aux notifications (Web Push) et notification d'essai."""

from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.push import InvalidSubscription, send_test, subscribe, unsubscribe
from prospection.config import Settings
from prospection.ui.deps import get_engine, get_http_client, get_now, get_settings
from prospection.ui.session import require_session

router = APIRouter(prefix="/notifications", dependencies=[Depends(require_session)])
ENGINE = Depends(get_engine)
BODY = Body(None)  # JSON envoyé par le navigateur, vérifié champ par champ


@router.post("/abonnement")
def add_phone(
    body: Any = BODY,
    engine: Engine = ENGINE,
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:
    try:
        subscribe(engine, body, now)
    except InvalidSubscription as error:
        return JSONResponse({"erreur": str(error)}, status_code=400)
    return Response(status_code=204)


@router.post("/desabonnement")
def remove_phone(body: Any = BODY, engine: Engine = ENGINE) -> Response:
    endpoint = body.get("endpoint") if isinstance(body, dict) else None
    if isinstance(endpoint, str):
        unsubscribe(engine, endpoint[:1000])
    return Response(status_code=204)


@router.post("/essai")
def test_notification(
    engine: Engine = ENGINE, client: httpx.Client = Depends(get_http_client),  # noqa: B008
    now: datetime = Depends(get_now), settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    keys = settings.vapid_keys()
    reached = send_test(engine, client, keys, now) if keys else 0
    return RedirectResponse(f"/reglages/rappels?essai={reached}", status_code=303)
