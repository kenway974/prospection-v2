"""Pages d'erreur en français, sans trace technique."""

import logging
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException

from prospection.ui.deps import templates
from prospection.ui.security import SECURITY_HEADERS
from prospection.ui.session import LoginRequired

logger = logging.getLogger(__name__)

DATABASE_DOWN = "La base de données ne répond pas. Réessayez dans un instant."
UNEXPECTED = (
    "Un problème est survenu. Réessayez dans un instant ; "
    "si ça continue, consultez les journaux Railway."
)


def _error_page(request: Request, message: str, status: int) -> Response:
    context = {"message": message}
    return templates.TemplateResponse(request, "erreur.html", context, status_code=status)


HTTP_MESSAGES = {
    404: "Page introuvable. Revenez à l'accueil.",
    405: "Action impossible sur cette page. Revenez à l'accueil.",
}
BAD_REQUEST = "La demande n'a pas pu aboutir. Revenez à l'accueil et réessayez."


async def _http_error(request: Request, exc: Exception) -> Response:
    status = exc.status_code if isinstance(exc, HTTPException) else 400
    return _error_page(request, HTTP_MESSAGES.get(status, BAD_REQUEST), status)


async def _login_required(request: Request, exc: Exception) -> Response:
    path = exc.path if isinstance(exc, LoginRequired) else "/"
    if request.headers.get("hx-request") == "true":
        # Requête HTMX : on recharge toute la page vers la connexion, en revenant
        # ensuite sur la page affichée (pas sur l'adresse de l'action).
        current = urlsplit(request.headers.get("hx-current-url", ""))
        same_site = current.netloc == request.headers.get("host")
        page = current.path if same_site and current.path.startswith("/") else "/"
        return Response(status_code=200, headers={"HX-Redirect": f"/connexion?suite={quote(page)}"})
    return RedirectResponse(f"/connexion?suite={quote(path)}", status_code=303)


async def _database_down(request: Request, exc: Exception) -> Response:
    logger.error("Base injoignable : %s", type(exc).__name__)
    return _error_page(request, DATABASE_DOWN, 503)


async def _unexpected(request: Request, exc: Exception) -> Response:
    # Starlette place ce gestionnaire hors des middlewares : en-têtes ajoutés ici.
    # La trace est journalisée par uvicorn, pas affichée.
    response = _error_page(request, UNEXPECTED, 500)
    response.headers.update(SECURITY_HEADERS)
    return response


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(LoginRequired, _login_required)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(OperationalError, _database_down)
    app.add_exception_handler(Exception, _unexpected)
