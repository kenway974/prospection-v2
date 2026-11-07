"""Page Stats des mails d'audit (C164)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import Engine

from prospection.application.mail_stats_page import stats_screen
from prospection.domain.mail_stats import MIN_SENDS
from prospection.ui.deps import get_engine, templates
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])


@router.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, engine: Engine = Depends(get_engine)) -> Response:  # noqa: B008
    context = {"tab": "prospects", "screen": stats_screen(engine), "min_sends": MIN_SENDS}
    return templates.TemplateResponse(request, "stats.html", context)
