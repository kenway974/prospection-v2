"""Mail d'audit envoyé à une sélection (C168) : ce qui partira, ce qui est écarté et
pourquoi, puis mise en file pour la tâche de fond (rien ne part depuis l'interface)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Connection, Engine

from prospection.application.audit_mail_context import GMAIL, SETTINGS
from prospection.application.mail_recipients import usable_recipients
from prospection.application.prospect_selection import MAX_SELECTION
from prospection.domain.mail_settings import sender_of
from prospection.storage.audit_mails import sent_at
from prospection.storage.mail_queue import enqueue, waiting_among
from prospection.storage.mail_settings import load_gmail, load_mail_settings
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox

SENT, QUEUED = "mail d'audit déjà envoyé", "déjà en file d'envoi"
NOT_AUDITED, TO_CHECK = "pas encore d'audit", "site à vérifier (plateforme ?)"


@dataclass(frozen=True)
class BatchRow:
    prospect_id: int
    name: str
    email: str | None  # adresse qui recevra le mail
    reason: str | None  # pourquoi il est écarté ; None : il part


@dataclass(frozen=True)
class BatchPreview:
    blocked: str | None  # empêche tout l'envoi (réglages, Gmail), dit quoi faire
    rows: list[BatchRow]


def batch_row(
    conn: Connection, prospect_id: int, pepper: bytes, waiting: set[int]
) -> BatchRow | None:
    prospect = load_prospect(conn, prospect_id)
    if prospect is None:
        return None
    name = str(prospect.data.get("name") or "")
    recipients, why = usable_recipients(conn, prospect, pepper)
    site = prospect.site
    reasons = [
        (sent_at(conn, prospect_id) is not None, SENT), (prospect_id in waiting, QUEUED),
        (site is None, NOT_AUDITED), (site is not None and site.unconfirmed, TO_CHECK),
        (why is not None, why),
    ]  # fmt: skip
    reason = next((r for failed, r in reasons if failed), None)
    return BatchRow(prospect_id, name, recipients[0] if recipients else None, reason)


def batch_preview(engine: Engine, box: SecretBox, prospect_ids: Sequence[int]) -> BatchPreview:
    ids = list(dict.fromkeys(prospect_ids))[:MAX_SELECTION]
    with engine.connect() as conn:
        settings, account = load_mail_settings(conn), load_gmail(conn)
        waiting = waiting_among(conn, ids)
        rows = [r for i in ids if (r := batch_row(conn, i, box.pepper, waiting))]
    blocked = SETTINGS if sender_of(settings) is None else GMAIL if account is None else None
    return BatchPreview(blocked, rows)


def queue_batch(engine: Engine, box: SecretBox, prospect_ids: Sequence[int], now: datetime) -> int:
    """Met en file les prospects qui peuvent recevoir le mail ; rend leur nombre."""
    preview = batch_preview(engine, box, prospect_ids)
    if preview.blocked:
        return 0
    with engine.begin() as conn:
        return enqueue(conn, [r.prospect_id for r in preview.rows if r.reason is None], now)
