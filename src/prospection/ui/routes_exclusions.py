"""Réglages : franchises à exclure et liste noire, un nom par ligne (C30, C33)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.exclusion_settings import TooManyNames, current_lists, save_lists
from prospection.ui.deps import get_engine, templates
from prospection.ui.session import require_session

router = APIRouter(prefix="/reglages", dependencies=[Depends(require_session)])
MAX_FORM_CHARS = 100_000


def _page(
    request: Request, franchises: str, blacklist: str, error: str | None, status_code: int
) -> Response:
    context = {"tab": "", "franchises": franchises, "blacklist": blacklist, "error": error}
    return templates.TemplateResponse(
        request, "reglages_exclusions.html", context, status_code=status_code
    )


@router.get("/exclusions", response_class=HTMLResponse)
def exclusions_page(request: Request, engine: Engine = Depends(get_engine)) -> Response:  # noqa: B008
    lists = current_lists(engine)
    return _page(request, "\n".join(lists.franchises), "\n".join(lists.blacklist), None, 200)


@router.post("/exclusions")
def save_exclusions(
    request: Request,
    franchises: str = Form("", max_length=MAX_FORM_CHARS),
    liste_noire: str = Form("", max_length=MAX_FORM_CHARS),
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Response:
    try:
        save_lists(engine, franchises, liste_noire)
    except TooManyNames as error:
        return _page(request, franchises, liste_noire, str(error), 400)
    return RedirectResponse("/reglages/exclusions", status_code=303)
