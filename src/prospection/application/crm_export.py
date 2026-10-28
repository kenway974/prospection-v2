"""Envoi des intéressés vers Notion par la tâche de fond (C67 à C75).

Le bouton « Exporter » met en file ; la tâche de fond envoie, au rythme permis par Notion.
Panne ou limite atteinte : nouvel essai plus tard, rien n'est perdu (C73). Refus : en échec
avec la raison (C74). Doublon : mis à jour sans écraser une saisie manuelle (C69, C70).
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.crm_target import NotionTarget, notion_target
from prospection.application.crm_values import crm_values
from prospection.crm.notion_pages import (
    NotionBusy,
    NotionRefused,
    create_page,
    find_page,
    update_page,
)
from prospection.domain.crm_record import merge, to_properties
from prospection.storage import crm_exports as store
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox

BATCH, PAUSE = 20, 0.35  # Notion : 3 requêtes par seconde en moyenne (C75)
RETRY = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2))
CREATED, UPDATED = "créé", "mis à jour"


@dataclass(frozen=True)
class Report:
    created: int
    updated: int
    failed: list[tuple[str, str]]  # entreprise, raison
    waiting: int


def queue_export(engine: Engine, prospect_ids: list[int], now: datetime) -> None:
    with engine.begin() as conn:
        store.queue(conn, prospect_ids, now)


def _send_one(engine: Engine, client: httpx.Client, target: NotionTarget, pid: int,
              now: datetime) -> None:  # fmt: skip
    with engine.connect() as conn:
        row, before = load_prospect(conn, pid), store.previous(conn, pid)
        values = crm_values(conn, row, now) if row else {}
    if row is None:
        with engine.begin() as conn:
            store.mark_failed(conn, pid, "Prospect supprimé entre-temps")
        return
    siren = values.get("SIREN")
    page = find_page(client, target.token, target.database_id, str(values["ID app"]), siren)
    if page is None:
        written = merge(None, {}, values)
        found = create_page(client, target.token, target.database_id,
                            to_properties(written, creating=True))  # fmt: skip
        outcome = CREATED
    else:
        update = merge(page.values, before.written, values)
        url = (
            update_page(client, target.token, page.id, to_properties(update, creating=False))
            if update
            else page.url
        )
        found, written, outcome = (page.id, url or page.url), {**before.written, **update}, UPDATED
    with engine.begin() as conn:
        store.mark_sent(conn, pid, found, written, outcome, now)


def send_pending(
    engine: Engine, box: SecretBox, client: httpx.Client, now: datetime, pause: float = PAUSE
) -> int:
    """Envoie jusqu'à BATCH prospects en file ; renvoie le nombre envoyé."""
    target = notion_target(engine, box)
    if target is None:
        return 0
    with engine.connect() as conn:
        ids = store.ready(conn, now, BATCH)
    sent = 0
    for pid in ids:
        try:
            _send_one(engine, client, target, pid, now)
            sent += 1
        except NotionBusy as busy:
            with engine.begin() as conn:
                attempts = store.previous(conn, pid).attempts
                delay = max(RETRY[min(attempts, len(RETRY) - 1)],
                            timedelta(seconds=busy.retry_after or 0))  # fmt: skip
                store.retry_at(conn, pid, now + delay, str(busy))
            break  # Notion est occupé : on laisse les suivants pour plus tard
        except NotionRefused as refused:
            with engine.begin() as conn:
                store.mark_failed(conn, pid, str(refused))
        time.sleep(pause)
    return sent


def export_report(engine: Engine) -> Report:
    with engine.connect() as conn:
        batch, waiting = store.last_batch(conn), store.waiting(conn)
    created = sum(1 for _, state, outcome, _ in batch if outcome == CREATED)
    updated = sum(1 for _, state, outcome, _ in batch if outcome == UPDATED)
    failed = [(name, error or "") for name, state, _, error in batch if state == store.FAILED]
    return Report(created, updated, failed, waiting)
