"""Écran Recherche : lancer une campagne (C08, C10 à C18)."""

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.budget_settings import search_readiness
from prospection.application.search_screen import estimate_raw, launch, synonyms, templates
from prospection.config import Settings
from prospection.domain.campaign_request import InvalidRequest, validate_request
from prospection.domain.google_cost import Pricing
from prospection.sources.geo_communes import GeoUnavailable, find_communes
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import (
    get_box,
    get_engine,
    get_http_client,
    get_now,
    get_pricing,
    get_settings,
)  # fmt: skip
from prospection.ui.deps import (
    templates as tpl,
)
from prospection.ui.formatting import euros
from prospection.ui.search_form import commune_value, parse_form, request_to_form
from prospection.ui.session import require_session

router = APIRouter(prefix="/recherche", dependencies=[Depends(require_session)])
NO_GOOGLE_KEY = "Ajoutez votre clé Google dans Réglages pour chercher sur Google Maps."
DEFAULTS = {"nombre": "20", "avis_max": "30", "site": "any", "telephone": "with",
            "franchises": "on", "synonymes": "on", "rayon": "0"}  # fmt: skip


def _page(
    request: Request, engine: Engine, box: SecretBox, values: dict[str, str],
    errors: dict[str, str] | None = None, status_code: int = 200,
) -> Response:  # fmt: skip
    context = {
        "tab": "search", "values": values, "errors": errors or {},
        "readiness": search_readiness(engine, box), "templates": templates(engine),
    }  # fmt: skip
    return tpl.TemplateResponse(request, "recherche.html", context, status_code=status_code)


@router.get("", response_class=HTMLResponse)
def search_page(
    request: Request, modele: str = "",
    engine: Engine = Depends(get_engine), box: SecretBox = Depends(get_box),  # noqa: B008
) -> Response:  # fmt: skip
    chosen = next((t for t in templates(engine) if t.name == modele), None)
    values = request_to_form(chosen.request) if chosen else dict(DEFAULTS)
    return _page(request, engine, box, values)


@router.get("/communes", response_class=HTMLResponse)
def communes(
    request: Request,
    ville: str = "",
    client: httpx.Client = Depends(get_http_client),  # noqa: B008
) -> Response:
    try:
        found = find_communes(client, ville)
        problem = None if found else "Aucune commune de ce nom. Vérifiez l'orthographe."
    except GeoUnavailable:
        found, problem = [], "Le service des communes ne répond pas. Réessayez dans un instant."
    choices = [(commune_value(c), c.label) for c in found]
    context = {"choices": choices, "problem": problem}
    return tpl.TemplateResponse(request, "_communes.html", context)


@router.get("/synonymes", response_class=HTMLResponse)
def synonyms_preview(request: Request, metiers: str = "") -> Response:
    return tpl.TemplateResponse(request, "_synonymes.html", {"queries": synonyms(metiers)})


@router.post("/estimation", response_class=HTMLResponse)
async def estimation(
    request: Request, engine: Engine = Depends(get_engine),  # noqa: B008
    pricing: Pricing = Depends(get_pricing), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    form = {k: str(v) for k, v in (await request.form()).items()}
    result = estimate_raw(engine, pricing, parse_form(form).raw, now, settings.timezone)
    context = {"estimate": result, "paid": euros(result.paid_cents)}
    return tpl.TemplateResponse(request, "_estimate.html", context)


@router.post("")
async def launch_campaign(
    request: Request, engine: Engine = Depends(get_engine),  # noqa: B008
    box: SecretBox = Depends(get_box), now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    form = {k: str(v)[:500] for k, v in (await request.form()).items()}
    parsed = parse_form(form)
    errors = dict(parsed.errors)
    try:
        campaign = validate_request(parsed.raw)
    except InvalidRequest as invalid:
        errors = {**invalid.errors, **errors}
    if not search_readiness(engine, box).has_google_key:
        errors["google"] = NO_GOOGLE_KEY
    if errors:
        return _page(request, engine, box, form, errors, 400)
    campaign_id = launch(engine, campaign, form.get("modele", ""), now)
    return RedirectResponse(f"/campagnes/{campaign_id}", status_code=303)
