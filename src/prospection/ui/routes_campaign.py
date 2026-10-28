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
from prospection.application.file_export import campaign_csv, campaign_xlsx
from prospection.config import Settings
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.formatting import euros, short_datetime
from prospection.ui.session import require_session

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    _progress(engine, campaign_id)
    request_stop(engine, campaign_id, now)
    return RedirectResponse(f"/campagnes/{campaign_id}", status_code=303)


def _download(data: bytes, kind: str, name: str) -> Response:
    disposition = f'attachment; filename="{name}"'
    return Response(data, media_type=kind, headers={"Content-Disposition": disposition})


@router.get("/{campaign_id}/export.csv")
def export_csv(
    campaign_id: int, liste: str = "prospects",
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    """C62, C65, C66 : prospects ou exclus ; aucun statut modifié (C118)."""
    _progress(engine, campaign_id)
    which = "exclus" if liste == "exclus" else "prospects"
    data = campaign_csv(engine, campaign_id, which, now, settings.timezone)
    return _download(data, "text/csv; charset=utf-8", f"campagne-{campaign_id}-{which}.csv")


@router.get("/{campaign_id}/export.xlsx")
def export_xlsx(
    campaign_id: int,
    engine: Engine = Depends(get_engine), now: datetime = Depends(get_now),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:  # fmt: skip
    _progress(engine, campaign_id)
    data = campaign_xlsx(engine, campaign_id, now, settings.timezone)
    return _download(data, XLSX, f"campagne-{campaign_id}.xlsx")
