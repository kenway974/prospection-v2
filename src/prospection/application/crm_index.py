"""Relire la base Notion pour exclure ce qui y est déjà (C32). Tâche de fond, toutes les heures."""

import logging
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.crm_target import notion_target
from prospection.crm.notion_pages import NotionBusy, NotionRefused, index_pages
from prospection.domain.trades import normalize
from prospection.storage.crm_index import APP_ID, NAME, SIREN, replace_index
from prospection.storage.secret_box import SecretBox

logger = logging.getLogger(__name__)
MAX_PAGES = 50  # 5 000 fiches au plus (rythme de Notion : crm.notion_pages.PACER)


def _name_key(name: str | None, city: str | None, bare: bool) -> set[tuple[str, str]]:
    """« nom|ville » ; le nom seul pour une fiche sans identifiant, SIREN ni ville."""
    if not name or not normalize(name):
        return set()
    if city and normalize(city):
        return {(NAME, f"{normalize(name)}|{normalize(city)}")}
    return {(NAME, normalize(name))} if bare else set()


def refresh_crm_index(engine: Engine, box: SecretBox, client: httpx.Client, now: datetime) -> int:
    """Nombre de fiches lues ; -1 si Notion n'est pas configuré ou ne répond pas (index gardé)."""
    target = notion_target(engine, box)
    if target is None:  # CRM désactivé : plus rien à exclure
        with engine.begin() as conn:
            replace_index(conn, set())
        return -1
    entries: set[tuple[str, str]] = set()
    cursor, count = None, 0
    try:
        for _ in range(MAX_PAGES):
            found, cursor = index_pages(client, target.token, target.database_id, cursor)
            for app_id, siren, name, city in found:
                entries |= {(APP_ID, app_id)} if app_id else set()
                entries |= {(SIREN, siren)} if siren else set()
                entries |= _name_key(name, city, bare=not (app_id or siren))
            count += len(found)
            if cursor is None:
                break
        else:  # trop de fiches : un index partiel ne remplace pas le complet
            logger.warning("CRM : plus de %s pages, index gardé tel quel", MAX_PAGES)
            return -1
    except (NotionBusy, NotionRefused):
        return -1  # index précédent gardé : on réessaiera
    with engine.begin() as conn:
        replace_index(conn, entries)
    return count
