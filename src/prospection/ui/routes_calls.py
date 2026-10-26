"""Saisies de la fiche d'appel, enregistrées tout de suite (C102 à C107).

Avec HTMX, la réponse est le bloc mis à jour (422 et message au champ si la saisie est
refusée, saisie gardée) ; sans HTMX, retour à la fiche.
"""

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import Engine

from prospection.application import call_actions as calls
from prospection.application.prospect_card import UnknownProspect, card
from prospection.config import Settings
from prospection.ui.call_views import card_context
from prospection.ui.deps import get_engine, get_now, get_settings, templates
from prospection.ui.session import require_session

router = APIRouter(dependencies=[Depends(require_session)])
ENGINE, NOW, SETTINGS = Depends(get_engine), Depends(get_now), Depends(get_settings)


def _save(
    request: Request, engine: Engine, prospect_id: int, now: datetime, settings: Settings,
    fragment: str, save: Callable[[], None], kept: Mapping[str, Any],
) -> Response:  # fmt: skip
    errors, status_code = {}, 200
    try:
        save()
    except calls.InvalidInput as refused:
        errors, status_code = {refused.field: refused.message}, 422
    except UnknownProspect:
        raise HTTPException(status_code=404) from None
    if "HX-Request" not in request.headers:
        return RedirectResponse(f"/prospects/{prospect_id}", status_code=303)
    shown = card(engine, prospect_id, None, "", now, remember=False)
    extra = kept if errors else {"saved": fragment.strip("_").removesuffix(".html")}
    context = card_context(shown, settings.timezone, "", errors=errors, **extra)
    return templates.TemplateResponse(request, fragment, context, status_code=status_code)


@router.post("/prospects/{prospect_id}/resultat")
def result(
    request: Request, prospect_id: int, statut: str = Form("", max_length=30),
    engine: Engine = ENGINE, now: datetime = NOW, settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    def save() -> None:
        calls.record_result(engine, prospect_id, statut, now, settings.timezone)

    return _save(request, engine, prospect_id, now, settings, "_suivi.html", save, {})


@router.post("/prospects/{prospect_id}/action")
def action(
    request: Request, prospect_id: int, type: str = Form("", max_length=30),
    date: str = Form("", max_length=20), heure: str = Form("", max_length=10),
    engine: Engine = ENGINE, now: datetime = NOW, settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    kept = {"action": {"type": type, "date": date, "heure": heure}}

    def save() -> None:
        calls.schedule(engine, prospect_id, type, date, heure, now)

    return _save(request, engine, prospect_id, now, settings, "_suivi.html", save, kept)


@router.post("/prospects/{prospect_id}/note")
def note(
    request: Request, prospect_id: int, texte: str = Form("", max_length=4000),
    engine: Engine = ENGINE, now: datetime = NOW, settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    def save() -> None:
        calls.save_note(engine, prospect_id, texte, now)

    return _save(
        request, engine, prospect_id, now, settings, "_notes.html", save, {"note_text": texte}
    )


@router.post("/prospects/{prospect_id}/contact")
def contact(
    request: Request, prospect_id: int, dirigeant: str = Form("", max_length=200),
    mobile: str = Form("", max_length=50), email: str = Form("", max_length=300),
    engine: Engine = ENGINE, now: datetime = NOW, settings: Settings = SETTINGS,
) -> Response:  # fmt: skip
    kept = {"contact": {"dirigeant": dirigeant, "mobile": mobile, "email": email}}

    def save() -> None:
        calls.save_contact(engine, prospect_id, dirigeant, mobile, email, now)

    return _save(request, engine, prospect_id, now, settings, "_contact.html", save, kept)


@router.post("/actions/{action_id}/terminer")
def finish(action_id: int, engine: Engine = ENGINE, now: datetime = NOW) -> Response:
    calls.finish_action(engine, action_id, now)
    return RedirectResponse("/", status_code=303)
