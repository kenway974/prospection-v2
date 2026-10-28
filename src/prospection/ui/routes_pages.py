"""Écrans principaux de l'app (protégés par la session)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import Engine

from prospection.application.alerts import current_alerts
from prospection.application.call_actions import today_screen
from prospection.application.connection_journal import JOURNAL_SIZE, latest_attempts
from prospection.config import Settings
from prospection.domain.call_status import ACTION_KINDS
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.formatting import long_day, short_datetime
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])
STATUS_LABELS = {"ok": "Réussie", "refused": "Refusée", "blocked": "Bloquée"}


def _page(request: Request, name: str, tab: str, **context: object) -> Response:
    return templates.TemplateResponse(request, name, {"tab": tab, **context})


@router.get("/", response_class=HTMLResponse)
def today(
    request: Request,
    terminee: int = 0,
    rouvrir: str = "",
    settings: Settings = Depends(get_settings),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:
    screen = today_screen(engine, now, settings.timezone)
    resume = screen.resume
    return _page(
        request, "aujourdhui.html", "today", day=long_day(now, settings.timezone),
        agenda=screen.agenda, resume=resume, kinds=ACTION_KINDS, finished=terminee,
        reopen_failed=rouvrir == "impossible", alerts=current_alerts(engine),
    )  # fmt: skip


@router.get("/reglages/connexions", response_class=HTMLResponse)
def connection_journal(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:
    rows = []
    for attempt in latest_attempts(engine):
        status = "blocked" if attempt.blocked else "ok" if attempt.success else "refused"
        when = short_datetime(attempt.at, settings.timezone)
        rows.append((when, attempt.ip, status, STATUS_LABELS[status]))
    return _page(request, "reglages_connexions.html", "", rows=rows, size=JOURNAL_SIZE)
