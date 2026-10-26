"""Écrans Prospects et fiche d'appel (C61, C109, C120)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import Engine

from prospection.application.prospect_card import UnknownProspect, card, prospect_list
from prospection.config import Settings
from prospection.domain.call_status import STATUSES
from prospection.ui.call_views import card_context, queue_query
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/prospects", dependencies=[Depends(require_session)])


def _status(statut: str) -> str | None:
    return statut if statut in STATUSES else None


@router.get("", response_class=HTMLResponse)
def prospects_page(
    request: Request, statut: str = "", q: str = "",
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:  # fmt: skip
    status, query = _status(statut), q[:100]
    listing = prospect_list(engine, status, query)
    context = {
        "tab": "prospects", "rows": listing.rows, "counts": listing.counts,
        "total": sum(listing.counts.values()), "statuses": STATUSES, "status": status,
        "query": query, "qs": queue_query(status, query),
    }  # fmt: skip
    return templates.TemplateResponse(request, "prospects.html", context)


@router.get("/{prospect_id}", response_class=HTMLResponse)
def card_page(
    request: Request, prospect_id: int, statut: str = "", q: str = "",
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    status, query = _status(statut), q[:100]
    try:
        shown = card(engine, prospect_id, status, query, now)
    except UnknownProspect:
        raise HTTPException(status_code=404) from None
    context = card_context(shown, settings.timezone, queue_query(status, query))
    return templates.TemplateResponse(request, "fiche.html", context)
