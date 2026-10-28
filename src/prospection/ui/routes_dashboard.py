"""Tableau de bord (C80) et journal de chaque campagne (C81)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import Engine

from prospection.application.campaigns import UnknownCampaign, progress
from prospection.application.dashboard import backup_status, dashboard, journal
from prospection.config import Settings
from prospection.ui.deps import get_engine, get_settings, templates
from prospection.ui.formatting import euros, short_datetime
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])
ENGINE = Depends(get_engine)
SETTINGS = Depends(get_settings)


@router.get("/tableau-de-bord", response_class=HTMLResponse)
def dashboard_page(
    request: Request, engine: Engine = ENGINE, settings: Settings = SETTINGS
) -> Response:
    board = dashboard(engine)
    lines = [(line.stats, short_datetime(line.stats.created_at, settings.timezone), line.rate,
              euros(line.stats.cost_cents),
              None if line.cost_per_qualified is None else euros(line.cost_per_qualified))
             for line in board.lines]  # fmt: skip
    per_qualified = None if board.cost_per_qualified is None else euros(board.cost_per_qualified)
    done_at, error = backup_status(engine)
    backup = {"configured": settings.backup_target() is not None, "error": error,
              "at": short_datetime(done_at, settings.timezone) if done_at else None}  # fmt: skip
    context = {"tab": "search", "board": board, "lines": lines, "spent": euros(board.cost_cents),
               "per_qualified": per_qualified, "backup": backup}  # fmt: skip
    return templates.TemplateResponse(request, "tableau_de_bord.html", context)


@router.get("/campagnes/{campaign_id}/journal", response_class=HTMLResponse)
def journal_page(
    request: Request, campaign_id: int, engine: Engine = ENGINE, settings: Settings = SETTINGS
) -> Response:
    try:
        state = progress(engine, campaign_id)
    except UnknownCampaign:
        raise HTTPException(status_code=404) from None
    events = [(short_datetime(e.at, settings.timezone), e.level, e.message)
              for e in journal(engine, campaign_id)]  # fmt: skip
    context = {"tab": "search", "id": campaign_id, "name": state.name, "events": events}
    return templates.TemplateResponse(request, "journal.html", context)
