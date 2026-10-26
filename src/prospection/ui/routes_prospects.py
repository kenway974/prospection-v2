"""Écrans Prospects, session d'appel et fiche (C61, C109, C120)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.prospect_card import (
    UnknownProspect,
    card,
    prospect_list,
    start_session,
)
from prospection.config import Settings
from prospection.domain.call_status import STATUSES
from prospection.storage.prospect_list import SORTS
from prospection.ui.call_views import card_context, list_query
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/prospects", dependencies=[Depends(require_session)])
SORT_LABELS = {"trouves": "Ordre de la recherche", "nom": "Nom", "ville": "Ville"}


def _choices(statut: str, tri: str) -> tuple[str | None, str]:
    return (statut if statut in STATUSES else None), (tri if tri in SORTS else "trouves")


@router.get("", response_class=HTMLResponse)
def prospects_page(
    request: Request, statut: str = "", q: str = "", tri: str = "",
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:  # fmt: skip
    (status, sort), query = _choices(statut, tri), q[:100]
    listing = prospect_list(engine, status, query, sort)
    context = {
        "tab": "prospects", "rows": listing.rows, "counts": listing.counts,
        "total": sum(listing.counts.values()), "statuses": STATUSES, "status": status,
        "query": query, "sort": sort, "sorts": SORT_LABELS, "qs": list_query(status, query, sort),
    }  # fmt: skip
    return templates.TemplateResponse(request, "prospects.html", context)


@router.get("/session")
def session_start(
    statut: str = "", q: str = "", tri: str = "",
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    """Démarre une session sur la liste affichée ; sa file ne bouge plus ensuite (C109)."""
    (status, sort), query = _choices(statut, tri), q[:100]
    first = start_session(engine, status, query, sort, now)
    if first is None:
        return RedirectResponse(f"/prospects?{list_query(status, query, sort)}", status_code=303)
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
