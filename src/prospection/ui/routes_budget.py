"""Réglages : plafond de dépense Google par mois, 0 € par défaut (C07)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.budget_settings import current_budget, set_budget
from prospection.domain.budget import InvalidBudget
from prospection.ui.deps import get_engine, templates
from prospection.ui.formatting import euros
from prospection.ui.session import require_session

router = APIRouter(prefix="/reglages", dependencies=[Depends(require_session)])


def _page(request: Request, engine: Engine, error: str | None, status_code: int) -> Response:
    cents = current_budget(engine)
    context = {"tab": "", "budget": euros(cents), "free_only": cents == 0, "error": error}
    return templates.TemplateResponse(
        request, "reglages_budget.html", context, status_code=status_code
    )


@router.get("/budget", response_class=HTMLResponse)
def budget_page(request: Request, engine: Engine = Depends(get_engine)) -> Response:  # noqa: B008
    return _page(request, engine, None, 200)


@router.post("/budget")
def save_budget_choice(
    request: Request,
    montant: str = Form(""),
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:
    try:
        set_budget(engine, montant)
    except InvalidBudget as error:
        return _page(request, engine, str(error), 400)
    return RedirectResponse("/reglages/budget", status_code=303)
