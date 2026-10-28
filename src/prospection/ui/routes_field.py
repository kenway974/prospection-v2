"""Écrans Terrain : recherche autour de moi, tournée, statut en un geste (C113 à C115)."""

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.call_actions import InvalidInput
from prospection.application.campaigns import UnknownCampaign, progress
from prospection.application.field_tour import field_tour, mark_stop, start_field
from prospection.config import Settings
from prospection.domain.campaign_request import InvalidRequest
from prospection.sources.address_search import find_address
from prospection.ui.deps import get_engine, get_http_client, get_now, get_settings, templates
from prospection.ui.field_form import FIELD_DEFAULTS, read_field_form
from prospection.ui.session import require_session

router = APIRouter(prefix="/terrain", dependencies=[Depends(require_session)])


def _form(request: Request, values: dict[str, str], errors: dict[str, str], code: int) -> Response:
    context = {"tab": "field", "values": values, "errors": errors}
    return templates.TemplateResponse(request, "terrain.html", context, status_code=code)


@router.get("", response_class=HTMLResponse)
def field_page(request: Request) -> Response:
    return _form(request, dict(FIELD_DEFAULTS), {}, 200)


@router.post("")
async def field_search(
    request: Request, engine: Engine = Depends(get_engine),  # noqa: B008
    client: httpx.Client = Depends(get_http_client), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    values = {k: str(v)[:200] for k, v in (await request.form()).items()}
    parsed, errors = read_field_form(values)
    if parsed is None and not errors:
        located = find_address(client, values.get("adresse", ""))
        if located is None:
            errors = {"adresse": "Adresse introuvable : précisez-la (numéro, rue, ville)."}
        else:
            found = {"lat": str(located.lat), "lon": str(located.lon), "lieu": located.label}
            parsed, _ = read_field_form({**values, **found})
    if parsed is None or errors:
        return _form(request, values, errors, 400)
    try:
        campaign_id = start_field(engine, parsed, now, settings.timezone)
    except InvalidRequest as invalid:
        return _form(request, values, invalid.errors, 400)
    return RedirectResponse(f"/terrain/{campaign_id}", status_code=303)


@router.get("/{campaign_id}", response_class=HTMLResponse)
def tour_page(
    request: Request, campaign_id: int, ouvert: str = "",
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    try:
        state = progress(engine, campaign_id)
    except UnknownCampaign:
        raise HTTPException(status_code=404) from None
    tour = field_tour(engine, campaign_id, now, settings.timezone, open_only=ouvert == "1")
    context = {"tab": "field", "id": campaign_id, "state": state, "tour": tour,
               "open_only": ouvert == "1"}  # fmt: skip
    return templates.TemplateResponse(request, "terrain_tournee.html", context)


@router.post("/arret/{prospect_id}")
def stop_result(
    prospect_id: int, choix: str = Form("", max_length=20), retour: str = Form("", max_length=20),
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    try:
        mark_stop(engine, prospect_id, choix, now, settings.timezone)
    except (InvalidInput, LookupError):
        raise HTTPException(status_code=400) from None
    back = f"/terrain/{retour}" if retour.isdigit() else "/terrain"
    return RedirectResponse(back, status_code=303)
