"""Écrans principaux de l'app (protégés par la session)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response

from prospection.ui.deps import templates
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])


@router.get("/", response_class=HTMLResponse)
def today(request: Request) -> Response:
    return templates.TemplateResponse(request, "aujourdhui.html", {})
