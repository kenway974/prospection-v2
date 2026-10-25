"""Choix du CRM et de la base Notion de destination (C05, C06, C09)."""

from dataclasses import dataclass

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.crm.notion import NotionDatabase, NotionUnavailable, list_notion_databases
from prospection.domain.crm_choice import Crm
from prospection.domain.services import Service
from prospection.storage.app_settings import AppSettings, load_app_settings, save_crm
from prospection.storage.secret_box import SecretBox

DEFAULT_DATABASE_TITLE = "Prospects v2"
ASK_FOR_NOTION_KEY = "Enregistrez d'abord votre jeton Notion dans Clés API."
NO_DATABASE = (
    "Aucune base visible : dans Notion, ouvrez « Prospects v2 », menu ••• → Connexions → "
    "ajoutez votre intégration."
)


class InvalidCrmChoice(ValueError):
    """Choix refusé ; le message dit quoi faire."""


@dataclass(frozen=True)
class CrmScreen:
    settings: AppSettings
    databases: list[NotionDatabase]
    selected_id: str | None
    problem: str | None


def _databases(
    engine: Engine, box: SecretBox, client: httpx.Client
) -> tuple[list[NotionDatabase], str | None]:
    token = read_key(engine, box, Service.NOTION)
    if token is None:
        return [], ASK_FOR_NOTION_KEY
    try:
        databases = list_notion_databases(client, token)
    except NotionUnavailable as error:
        return [], str(error)
    return databases, None if databases else NO_DATABASE


def crm_screen(engine: Engine, box: SecretBox, client: httpx.Client) -> CrmScreen:
    with engine.connect() as conn:
        settings = load_app_settings(conn)
    databases, problem = _databases(engine, box, client)
    selected = settings.notion_database_id or next(
        (db.id for db in databases if db.title == DEFAULT_DATABASE_TITLE), None
    )
    return CrmScreen(settings, databases, selected, problem)


def choose_crm(
    engine: Engine, box: SecretBox, client: httpx.Client, crm: Crm, database_id: str
) -> None:
    if crm is Crm.NONE:
        with engine.begin() as conn:
            save_crm(conn, Crm.NONE, None, None)
        return
    if not database_id:
        raise InvalidCrmChoice("Choisissez la base Notion de destination.")
    databases, problem = _databases(engine, box, client)
    chosen = next((db for db in databases if db.id == database_id), None)
    if chosen is None:
        raise InvalidCrmChoice(problem or "Cette base n'est pas visible par l'intégration Notion.")
    with engine.begin() as conn:
        save_crm(conn, Crm.NOTION, chosen.id, chosen.title)
