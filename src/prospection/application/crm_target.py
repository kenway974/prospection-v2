"""Base Notion configurée (clé et base choisie), ou None."""

from dataclasses import dataclass

from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.domain.crm_choice import Crm
from prospection.domain.services import Service
from prospection.storage.app_settings import load_app_settings
from prospection.storage.secret_box import SecretBox


@dataclass(frozen=True)
class NotionTarget:
    token: str
    database_id: str


def notion_target(engine: Engine, box: SecretBox) -> NotionTarget | None:
    with engine.connect() as conn:
        settings = load_app_settings(conn)
    token = read_key(engine, box, Service.NOTION)
    if settings.crm != Crm.NOTION or not settings.notion_database_id or not token:
        return None
    return NotionTarget(token, settings.notion_database_id)
