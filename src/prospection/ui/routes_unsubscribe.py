"""Page publique de désinscription du mail d'audit (C148), sans connexion.

Seule action acceptée hors de l'app (Gmail l'appelle en un clic, sans origine) : le jeton
aléatoire de l'envoi sert de clé. L'ouverture de la page ne change rien ; il faut confirmer
(les antivirus qui ouvrent les liens ne désinscrivent personne).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import Engine

from prospection.application.unsubscribe import unsubscribe
from prospection.ui.deps import get_engine, get_now, templates

PREFIX = "/desinscription/"
router = APIRouter()


@router.get(PREFIX + "{token}", response_class=HTMLResponse)
def unsubscribe_page(request: Request, token: str) -> Response:
    return templates.TemplateResponse(request, "desinscription.html", {"token": token[:64]})


@router.post(PREFIX + "{token}", response_class=HTMLResponse)
def confirm_unsubscribe(
    request: Request, token: str, engine: Engine = Depends(get_engine),  # noqa: B008
    now: datetime = Depends(get_now),  # noqa: B008
) -> Response:  # fmt: skip
    done = unsubscribe(engine, token, now)
    return templates.TemplateResponse(request, "desinscription.html", {"done": done},
                                      status_code=200 if done else 404)  # fmt: skip
