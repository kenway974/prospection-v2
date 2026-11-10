"""Mail d'audit envoyé à une sélection (C168), avec son SMS (C177) : ce qui partira, ce qui
est écarté et pourquoi, puis mise en file pour la tâche de fond (rien ne part d'ici)."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import Connection, Engine

from prospection.application.api_keys import read_key
from prospection.application.audit_mail_context import GMAIL, SETTINGS
from prospection.application.mail_recipients import NO_VALID, usable_recipients
from prospection.application.prospect_selection import MAX_SELECTION
from prospection.application.sms_eligibility import sms_target
from prospection.domain.mail_settings import sender_of
from prospection.domain.services import Service
from prospection.domain.sms_settings import SmsSettings
from prospection.storage.audit_mails import sent_at
from prospection.storage.mail_queue import enqueue, waiting_among
from prospection.storage.mail_settings import load_gmail, load_mail_settings
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox
from prospection.storage.sms_queue_store import enqueue_sms, sms_waiting
from prospection.storage.sms_settings_store import load_sms_settings

SENT, QUEUED = "mail d'audit déjà envoyé", "déjà en file d'envoi"
NOT_AUDITED, TO_CHECK = "pas encore d'audit", "site à vérifier (plateforme ?)"


@dataclass(frozen=True)
class BatchRow:
    prospect_id: int
    name: str
    email: str | None  # adresse qui recevra le mail
    reason: str | None  # pourquoi il est écarté ; None : il part
    sms_reason: str | None = "SMS non prévu"  # None : le SMS part (C177)

    @property
    def leaves(self) -> bool:
        """Le mail ou le SMS part."""
        return self.reason is None or self.sms_reason is None


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


def _with_sms(conn: Connection, row: BatchRow, sms: SmsSettings, has_key: bool,
              my_phone: str | None, pepper: bytes) -> BatchRow:  # fmt: skip
    """Le SMS part avec le mail, ou seul quand il n'y a pas d'adresse (C177)."""
    if row.reason not in (None, NO_VALID):
        return replace(row, sms_reason=row.reason)
    prospect = load_prospect(conn, row.prospect_id)
    if prospect is None:
        return row
    if sms_waiting(conn, row.prospect_id):
        return replace(row, sms_reason=QUEUED)
    target = sms_target(conn, prospect, sms, has_key, my_phone, pepper)
    return replace(row, sms_reason=target.reason)


def batch_preview(engine: Engine, box: SecretBox, prospect_ids: Sequence[int]) -> BatchPreview:
    ids = list(dict.fromkeys(prospect_ids))[:MAX_SELECTION]
    has_key = read_key(engine, box, Service.BREVO) is not None
    with engine.connect() as conn:
        settings, account = load_mail_settings(conn), load_gmail(conn)
        sms = load_sms_settings(conn)
        waiting = waiting_among(conn, ids)
        rows = [_with_sms(conn, r, sms, has_key, settings.phone, box.pepper)
                for i in ids if (r := batch_row(conn, i, box.pepper, waiting))]  # fmt: skip
    blocked = SETTINGS if sender_of(settings) is None else GMAIL if account is None else None
    return BatchPreview(blocked, rows)


def queue_batch(engine: Engine, box: SecretBox, prospect_ids: Sequence[int], now: datetime) -> int:
    """Met en file les mails et les SMS qui peuvent partir ; rend le nombre de prospects."""
    preview = batch_preview(engine, box, prospect_ids)
    if preview.blocked:
        return 0
    mails = [r.prospect_id for r in preview.rows if r.reason is None]
    texts = [(r.prospect_id, r.reason is None) for r in preview.rows if r.sms_reason is None]
    with engine.begin() as conn:
        enqueue(conn, mails, now)
        enqueue_sms(conn, texts, now)
    return len(set(mails) | {p for p, _ in texts})
