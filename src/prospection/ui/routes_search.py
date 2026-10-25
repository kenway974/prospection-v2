"""Écran Recherche : lancer une campagne (C08, C10 à C18)."""

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.budget_settings import search_readiness
from prospection.application.campaigns import latest_campaigns
from prospection.application.search_screen import (
    TemplateNameTaken,
    estimate_raw,
    find_city,
    launch,
    synonyms,
    templates,
)
from prospection.domain.campaign_request import InvalidRequest, validate_request
from prospection.domain.criteria import Criteria
from prospection.domain.foreign_zones import countries
from prospection.domain.google_cost import Pricing
from prospection.storage.secret_box import SecretBox
from prospection.ui.deps import (
    get_box,
    get_engine,
    get_http_client,
    get_now,
    get_pricing,
)  # fmt: skip
from prospection.ui.deps import (
    templates as tpl,
)
from prospection.ui.formatting import euros
from prospection.ui.search_form import (
    MAX_FIELD,
    commune_value,
    criteria_to_form,
    parse_form,
    request_to_form,
)
from prospection.ui.session import require_session

router = APIRouter(prefix="/recherche", dependencies=[Depends(require_session)])
NO_GOOGLE_KEY = "Ajoutez votre clé Google dans Réglages pour chercher sur Google Maps."
DEFAULTS = {
    **criteria_to_form(Criteria()),
    "nombre": "20",
    "synonymes": "on",
    "rayon": "0",
    "pays": "FR",
}


async def _read_form(request: Request) -> dict[str, str]:
    """Champs du formulaire, chacun borné : une saisie démesurée ne coûte rien à traiter."""
    return {k: str(v)[:MAX_FIELD] for k, v in (await request.form()).items()}


def _page(
    request: Request, engine: Engine, box: SecretBox, values: dict[str, str],
    errors: dict[str, str] | None = None, status_code: int = 200,
) -> Response:  # fmt: skip
    context = {
        "tab": "search", "values": values, "errors": errors or {},
        "readiness": search_readiness(engine, box), "templates": templates(engine),
        "campaigns": latest_campaigns(engine), "countries": countries(),
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
    pays: str = "FR",
    client: httpx.Client = Depends(get_http_client),  # noqa: B008
) -> Response:
    result = find_city(client, ville, pays)
    choices = [(commune_value(c), c.label) for c in result.choices]
    context = {"choices": choices, "problem": result.problem}
    return tpl.TemplateResponse(request, "_communes.html", context)


@router.get("/synonymes", response_class=HTMLResponse)
def synonyms_preview(request: Request, metiers: str = "") -> Response:
    return tpl.TemplateResponse(request, "_synonymes.html", {"queries": synonyms(metiers)})


@router.post("/estimation", response_class=HTMLResponse)
async def estimation(
    request: Request, engine: Engine = Depends(get_engine),  # noqa: B008
    pricing: Pricing = Depends(get_pricing), now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    form = await _read_form(request)
    result = estimate_raw(engine, pricing, parse_form(form).raw, now)
    context = {"estimate": result, "paid": euros(result.paid_cents)}
    return tpl.TemplateResponse(request, "_estimate.html", context)


@router.post("")
async def launch_campaign(
    request: Request, engine: Engine = Depends(get_engine),  # noqa: B008
    box: SecretBox = Depends(get_box), now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    form = await _read_form(request)
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
    try:
        campaign_id = launch(engine, campaign, form.get("modele", ""), now)
    except TemplateNameTaken as taken:
        return _page(request, engine, box, form, {"modele": str(taken)}, 400)
    return RedirectResponse(f"/campagnes/{campaign_id}", status_code=303)
