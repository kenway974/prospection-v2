"""Abonnement du téléphone aux notifications (Web Push) et notification d'essai."""

import json
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.push import send_test
from prospection.application.push_subscriptions import (
    InvalidSubscription,
    subscribe,
    unsubscribe,
)
from prospection.config import Settings
from prospection.ui.deps import get_engine, get_http_client, get_now, get_settings
from prospection.ui.session import require_session

router = APIRouter(prefix="/notifications", dependencies=[Depends(require_session)])
ENGINE = Depends(get_engine)
MAX_BODY = 4096  # un abonnement fait moins de 1 Ko


class _TooLarge(Exception):
    pass


async def _json(request: Request) -> Any:
    """Corps JSON lu par morceaux, après la vérification de session, 4 Ko au plus."""
    size = request.headers.get("content-length", "")
    if size.isdigit() and int(size) > MAX_BODY:
        raise _TooLarge
    chunks, total = [], 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_BODY:
            raise _TooLarge
        chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks) or b"null")
    except ValueError:
        return None


@router.post("/abonnement")
async def add_phone(
    request: Request,
    engine: Engine = ENGINE,
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:
    try:
        await run_in_threadpool(subscribe, engine, await _json(request), now)
    except _TooLarge:
        return JSONResponse({"erreur": "Abonnement trop volumineux."}, status_code=413)
    except InvalidSubscription as error:
        return JSONResponse({"erreur": str(error)}, status_code=400)
    return Response(status_code=204)


@router.post("/desabonnement")
async def remove_phone(request: Request, engine: Engine = ENGINE) -> Response:
    try:
        body = await _json(request)
    except _TooLarge:
        return Response(status_code=413)
    endpoint = body.get("endpoint") if isinstance(body, dict) else None
    if isinstance(endpoint, str):
        await run_in_threadpool(unsubscribe, engine, endpoint[:1000])
    return Response(status_code=204)


@router.post("/essai")
def test_notification(
    engine: Engine = ENGINE, client: httpx.Client = Depends(get_http_client),  # noqa: B008
    now: datetime = Depends(get_now), settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    keys = settings.vapid_keys()
    reached = send_test(engine, client, keys, now) if keys else 0
    return RedirectResponse(f"/reglages/rappels?essai={reached}", status_code=303)
