"""Pages d'erreur en français, sans trace technique."""

import logging
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.exc import OperationalError

from prospection.ui.deps import templates
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


async def _login_required(request: Request, exc: Exception) -> Response:
    path = exc.path if isinstance(exc, LoginRequired) else "/"
    return RedirectResponse(f"/connexion?suite={quote(path)}", status_code=303)


async def _database_down(request: Request, exc: Exception) -> Response:
    logger.error("Base injoignable : %s", type(exc).__name__)
    return _error_page(request, DATABASE_DOWN, 503)


async def _unexpected(request: Request, exc: Exception) -> Response:
    logger.exception("Erreur inattendue")
    return _error_page(request, UNEXPECTED, 500)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(LoginRequired, _login_required)
    app.add_exception_handler(OperationalError, _database_down)
    app.add_exception_handler(Exception, _unexpected)
