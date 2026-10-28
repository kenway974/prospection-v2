"""Relire la base Notion pour exclure ce qui y est déjà (C32). Tâche de fond, toutes les heures."""

from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.crm_target import notion_target
from prospection.crm.notion_pages import NotionBusy, NotionRefused, index_pages
from prospection.domain.trades import normalize
from prospection.storage.crm_index import APP_ID, NAME, SIREN, replace_index
from prospection.storage.secret_box import SecretBox

MAX_PAGES = 50  # 5 000 fiches au plus (rythme de Notion : crm.notion_pages.PACER)


def refresh_crm_index(engine: Engine, box: SecretBox, client: httpx.Client, now: datetime) -> int:
    """Nombre de fiches lues ; -1 si Notion n'est pas configuré ou ne répond pas (index gardé)."""
    target = notion_target(engine, box)
    if target is None:
        return -1
    entries: set[tuple[str, str]] = set()
    cursor, count = None, 0
    try:
        for _ in range(MAX_PAGES):
            found, cursor = index_pages(client, target.token, target.database_id, cursor)
            for app_id, siren, name in found:
                entries |= {(APP_ID, app_id)} if app_id else set()
                entries |= {(SIREN, siren)} if siren else set()
                entries |= {(NAME, normalize(name))} if name and normalize(name) else set()
            count += len(found)
            if cursor is None:
                break
    except (NotionBusy, NotionRefused):
        return -1  # index précédent gardé : on réessaiera
    with engine.begin() as conn:
        replace_index(conn, entries)
    return count
