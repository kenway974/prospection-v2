"""Page publique de l'app et de sa politique de confidentialité (C151), sans connexion.

Sert de page d'accueil et de règles de confidentialité sur l'écran de consentement Google
(publication de l'accès Gmail). Texte fixe : rien ne vient de la base.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from prospection.ui.deps import templates

router = APIRouter()


@router.get("/confidentialite-app", response_class=HTMLResponse)
def public_privacy(request: Request) -> Response:
    return templates.TemplateResponse(request, "confidentialite_app.html", {})
