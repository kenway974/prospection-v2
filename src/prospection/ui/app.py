"""Construction de l'application web."""

from fastapi import FastAPI
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.ui import routes_health
from prospection.ui.security import (
    HttpsOnlyMiddleware,
    SameOriginMiddleware,
    SecurityHeadersMiddleware,
)


def create_app(settings: Settings, engine: Engine) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.engine = engine
    app.include_router(routes_health.router)
    app.add_middleware(SameOriginMiddleware)
    if settings.behind_proxy:
        app.add_middleware(HttpsOnlyMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    return app
