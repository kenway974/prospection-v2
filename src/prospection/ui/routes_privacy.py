"""Confidentialité : durée avant purge (C94), suppression d'une entreprise (C95)."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application.privacy import (
    InvalidPurge,
    change_purge_months,
    company_name,
    erase_company,
    purge_months,
)
from prospection.ui.deps import get_engine, templates
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])
ENGINE = Depends(get_engine)


def _settings(
    request: Request, engine: Engine, error: str | None, code: int, erased: int = 0
) -> Response:
    context = {"tab": "", "months": purge_months(engine), "error": error, "erased": erased}
    return templates.TemplateResponse(
        request, "reglages_confidentialite.html", context, status_code=code
    )


@router.get("/reglages/confidentialite", response_class=HTMLResponse)
def privacy_page(request: Request, supprime: int = 0, engine: Engine = ENGINE) -> Response:
    return _settings(request, engine, None, 200, supprime)


@router.post("/reglages/confidentialite")
def save_privacy(
    request: Request, mois: str = Form("", max_length=5), engine: Engine = ENGINE
) -> Response:
    try:
        change_purge_months(engine, mois)
    except InvalidPurge as error:
        return _settings(request, engine, str(error), 400)
    return RedirectResponse("/reglages/confidentialite", status_code=303)


@router.get("/prospects/{prospect_id}/supprimer", response_class=HTMLResponse)
def erase_page(request: Request, prospect_id: int, engine: Engine = ENGINE) -> Response:
    name = company_name(engine, prospect_id)
    if name is None:
        raise HTTPException(status_code=404)
    context = {"tab": "prospects", "id": prospect_id, "name": name}
    return templates.TemplateResponse(request, "supprimer.html", context)


@router.post("/prospects/{prospect_id}/supprimer")
def erase(prospect_id: int, engine: Engine = ENGINE) -> Response:
    count = erase_company(engine, prospect_id)
    if not count:
        raise HTTPException(status_code=404)
    return RedirectResponse(f"/reglages/confidentialite?supprime={count}", status_code=303)
