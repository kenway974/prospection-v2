"""Construction de l'application web."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.storage.secret_box import SecretBox
from prospection.ui import (
    routes_auth,
    routes_crm,
    routes_health,
    routes_pages,
    routes_settings,
)
from prospection.ui.cookies import SessionRefreshMiddleware
from prospection.ui.errors import install_error_handlers
from prospection.ui.paths import STATIC_DIR
from prospection.ui.security import (
    HttpsOnlyMiddleware,
    SameOriginMiddleware,
    SecurityHeadersMiddleware,
)


def create_app(settings: Settings, engine: Engine) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.engine = engine
    app.state.box = SecretBox(settings.encryption_key.get_secret_value())
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for module in (routes_health, routes_auth, routes_pages, routes_settings, routes_crm):
        app.include_router(module.router)
    install_error_handlers(app)
    app.add_middleware(SessionRefreshMiddleware)
    app.add_middleware(SameOriginMiddleware)
    if settings.behind_proxy:
        app.add_middleware(HttpsOnlyMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    return app
