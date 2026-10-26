"""Suivi en direct d'une campagne (C34, C35, C37, C119)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.campaigns import (
    Progress,
    UnknownCampaign,
    progress,
    request_stop,
)
from prospection.config import Settings
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.formatting import euros, short_datetime
from prospection.ui.session import require_session

router = APIRouter(prefix="/campagnes", dependencies=[Depends(require_session)])


def _progress(engine: Engine, campaign_id: int) -> Progress:
    try:
        return progress(engine, campaign_id)
    except UnknownCampaign:
        raise HTTPException(status_code=404) from None


def _context(state: Progress, campaign_id: int, settings: Settings) -> dict[str, object]:
    events = [(short_datetime(e.at, settings.timezone), e.message) for e in state.recent_events]
    return {
        "tab": "search", "id": campaign_id, "state": state, "spent": euros(state.cost_cents),
        "running": state.status in {"queued", "running", "stopping"}, "events": events,
    }  # fmt: skip


@router.get("/{campaign_id}", response_class=HTMLResponse)
def campaign_page(
    request: Request, campaign_id: int,
    engine: Engine = Depends(get_engine), settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    context = _context(_progress(engine, campaign_id), campaign_id, settings)
    return templates.TemplateResponse(request, "suivi.html", context)


@router.get("/{campaign_id}/progression", response_class=HTMLResponse)
def campaign_progress(
    request: Request, campaign_id: int,
    engine: Engine = Depends(get_engine), settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    context = _context(_progress(engine, campaign_id), campaign_id, settings)
    return templates.TemplateResponse(request, "_progress.html", context)


@router.post("/{campaign_id}/arreter")
def stop(
    campaign_id: int,
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    _progress(engine, campaign_id)
    request_stop(engine, campaign_id, now)
    return RedirectResponse(f"/campagnes/{campaign_id}", status_code=303)
