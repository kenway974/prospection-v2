"""Envoi des intéressés vers Notion par la tâche de fond (C67 à C75).

Le bouton « Exporter » met en file ; la tâche de fond réserve et envoie, au rythme permis
par Notion (C75). Panne, limite ou refus général (clé, base) : la file est gardée et l'envoi
reprend plus tard (C73). Refus d'un prospect : en échec avec la raison (C74). Doublon : mis
à jour sans écraser une saisie manuelle, et une valeur devenue vide est vidée (C69, C70).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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
from prospection.domain.call_status import EXPORTED, INTERESTED
from prospection.domain.crm_record import merge, to_properties, written_after
from prospection.storage import crm_exports as store
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox

BATCH, LEASE = 20, timedelta(minutes=10)
RETRY = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2))
GENERAL_PAUSE = timedelta(minutes=30)
CREATED, UPDATED = "créé", "mis à jour"
_pause: dict[
    str, datetime
] = {}  # Notion : pas de nouvel envoi avant cette date (tout le processus)


def reset_pause() -> None:
    _pause.clear()


@dataclass(frozen=True)
class Report:
    created: int
    updated: int
    failed: list[tuple[str, str]]  # entreprise, raison
    waiting: int
    problem: str | None = None  # pourquoi la file attend (clé refusée, Notion en panne…)


def queue_export(engine: Engine, prospect_ids: list[int], now: datetime) -> None:
    with engine.begin() as conn:
        store.queue(conn, prospect_ids, now)


def _send_one(engine: Engine, client: httpx.Client, target: NotionTarget, pid: int,
              now: datetime, today: str, pepper: bytes) -> None:  # fmt: skip
    with engine.connect() as conn:
        row = load_prospect(conn, pid)
        if row is None or row.status not in (INTERESTED, EXPORTED):  # C67 : relu à l'envoi
            values = None
        else:
            values = crm_values(conn, row, now, today, pepper)
    if values is None:
        with engine.begin() as conn:
            store.mark_failed(conn, pid, "N'est plus intéressé")
        return
    page = find_page(client, target.token, target.database_id, str(values["ID app"]),
                     values.get("SIREN"))  # fmt: skip
    if page is None:
        update = merge(None, {}, values)
        found = create_page(client, target.token, target.database_id,
                            to_properties(update, creating=True))  # fmt: skip
        before: dict[str, object] = {}
        outcome = CREATED
    else:
        with engine.connect() as conn:
            before = store.page_written(conn, page.id)
        update = merge(page.values, before, values)
        url = page.url
        if update:
            url = update_page(client, target.token, page.id, to_properties(update, creating=False))
        found, outcome = (page.id, url or page.url), UPDATED
    written = written_after(page.values if page else None, before, values, update)
    with engine.begin() as conn:
        store.mark_sent(conn, pid, found, written, outcome, now)


def send_pending(
    engine: Engine, box: SecretBox, client: httpx.Client, now: datetime,
    timezone: str = "Europe/Paris",
) -> int:  # fmt: skip
    """Envoie jusqu'à BATCH prospects réservés ; renvoie le nombre envoyé."""
    target = notion_target(engine, box)
    if target is None or now < _pause.get("until", now):
        return 0
    with engine.begin() as conn:
        ids = store.claim_ready(conn, now, BATCH, LEASE)
    today, sent = now.astimezone(ZoneInfo(timezone)).date().isoformat(), 0
    for pid in ids:
        try:
            _send_one(engine, client, target, pid, now, today, box.pepper)
            sent += 1
        except NotionBusy as busy:
            with engine.begin() as conn:
                attempts = store.previous(conn, pid).attempts
                delay = max(RETRY[min(attempts, len(RETRY) - 1)],
                            timedelta(seconds=busy.retry_after or 0))  # fmt: skip
                store.retry_at(conn, pid, now + delay, str(busy))
            _pause["until"] = now + timedelta(seconds=busy.retry_after or 0)
            break  # Notion est occupé : les suivants attendent aussi
        except NotionRefused as refused:
            with engine.begin() as conn:
                if refused.general:  # clé ou base : rien à reprocher à ce prospect
                    store.retry_at(conn, pid, now + GENERAL_PAUSE, str(refused))
                else:
                    store.mark_failed(conn, pid, str(refused))
            if refused.general:
                _pause["until"] = now + GENERAL_PAUSE
                break
    return sent


def export_report(engine: Engine) -> Report:
    with engine.connect() as conn:
        batch, waiting = store.last_batch(conn), store.waiting(conn)
        failed, problem = store.failures(conn), store.waiting_problem(conn)
    created = sum(1 for _, _, outcome, _ in batch if outcome == CREATED)
    updated = sum(1 for _, _, outcome, _ in batch if outcome == UPDATED)
    return Report(created, updated, failed, waiting, problem if waiting else None)
