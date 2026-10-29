"""Écrans Prospects, session d'appel et fiche (C61, C109, C120, C127, C128)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.prospect_card import UnknownProspect, card
from prospection.application.prospect_listing import prospect_list, start_session
from prospection.application.prospect_view import SCORE
from prospection.config import Settings
from prospection.domain.call_status import STATUSES
from prospection.domain.prospect_source import SOURCES
from prospection.ui.call_views import card_context, list_query, list_scope, scope_params
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/prospects", dependencies=[Depends(require_session)])
SORT_LABELS = {"trouves": "Ordre de la recherche", SCORE: "Score (meilleures d'abord)",
               "nom": "Nom", "ville": "Ville"}  # fmt: skip


def _choices(statut: str, tri: str) -> tuple[str | None, str]:
    return (statut if statut in STATUSES else None), (tri if tri in SORT_LABELS else "trouves")


@router.get("", response_class=HTMLResponse)
def prospects_page(
    request: Request, statut: str = "", q: str = "", tri: str = "", origine: str = "",
    campagne: str = "", supprime: int = 0,
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    (status, sort), query, scope = _choices(statut, tri), q[:100], list_scope(origine, campagne)
    listing = prospect_list(engine, status, query, sort, now, settings.timezone, scope)
    context = {
        "tab": "prospects", "rows": listing.rows, "counts": listing.counts,
        "total": sum(listing.counts.values()), "statuses": STATUSES, "status": status,
        "query": query, "sort": sort, "sorts": SORT_LABELS, "summaries": listing.summaries,
        "sources": listing.sources, "source_labels": SOURCES, "campaigns": listing.campaigns,
        "scope": listing.scope, "here": scope_params(listing.scope),
        "deleted": max(supprime, 0), "any_prospect": listing.any_prospect,
        "groups": listing.groups,
    }  # fmt: skip
    return templates.TemplateResponse(request, "prospects.html", context)


@router.post("/session")
def session_start(
    statut: str = Form("", max_length=30), q: str = Form("", max_length=200),
    tri: str = Form("", max_length=20), origine: str = Form("", max_length=20),
    campagne: str = Form("", max_length=20),
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    """Démarre une session sur la liste affichée ; sa file ne bouge plus ensuite (C109)."""
    (status, sort), query, scope = _choices(statut, tri), q[:100], list_scope(origine, campagne)
    first = start_session(engine, status, query, sort, now, settings.timezone, scope)
    if first is None:
        where = list_query(status, query, sort, scope)
        return RedirectResponse(f"/prospects?{where}", status_code=303)
    return RedirectResponse(f"/prospects/{first}?session=1", status_code=303)


@router.get("/{prospect_id}", response_class=HTMLResponse)
def card_page(
    request: Request, prospect_id: int, session: int = 0,
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    try:
        shown = card(engine, prospect_id, now, settings.timezone, in_session=session == 1)
    except UnknownProspect:
        raise HTTPException(status_code=404) from None
    return templates.TemplateResponse(request, "fiche.html", card_context(shown, settings.timezone))
