"""Dépendances communes des routes (horloge, base, réglages)."""

from datetime import UTC, datetime

from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine

from prospection.config import Settings
from prospection.storage.secret_box import SecretBox
from prospection.ui.paths import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def get_now() -> datetime:
    return datetime.now(UTC)


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_engine(request: Request) -> Engine:
    engine: Engine = request.app.state.engine
    return engine


def get_box(request: Request) -> SecretBox:
    box: SecretBox = request.app.state.box
    return box
