"""Écrans principaux de l'app (protégés par la session)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.storage.login_journal import recent_attempts
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.formatting import long_day, short_datetime
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])
JOURNAL_SIZE = 50


def _page(request: Request, name: str, tab: str, **context: object) -> Response:
    return templates.TemplateResponse(request, name, {"tab": tab, **context})


@router.get("/", response_class=HTMLResponse)
def today(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:
    return _page(request, "aujourdhui.html", "today", day=long_day(now, settings.timezone))


@router.get("/prospects", response_class=HTMLResponse)
def prospects(request: Request) -> Response:
    return _page(request, "prospects.html", "prospects")


@router.get("/terrain", response_class=HTMLResponse)
def field(request: Request) -> Response:
    return _page(request, "terrain.html", "field")


@router.get("/recherche", response_class=HTMLResponse)
def search(request: Request) -> Response:
    return _page(request, "recherche.html", "search")


@router.get("/reglages/connexions", response_class=HTMLResponse)
def connection_journal(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:
    with engine.connect() as conn:
        attempts = recent_attempts(conn, JOURNAL_SIZE)
    rows = [(short_datetime(a.at, settings.timezone), a.ip, a.success) for a in attempts]
    return _page(request, "reglages_connexions.html", "", rows=rows)
