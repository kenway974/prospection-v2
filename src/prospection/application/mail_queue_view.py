"""Page « Envois » (C169, C170) : la file du mail d'audit, son plafond, son arrêt."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.send_pace import local_day_start
from prospection.storage import mail_queue as queue
from prospection.storage import mail_queue_settings as settings
from prospection.storage.sms_queue_store import cancel_sms_after_mail, recent_sms

SHOWN = 200
MAX_LIMIT = 200
LABELS = {queue.WAITING: "En attente", queue.SENT: "Envoyé", queue.FAILED: "Échec",
          queue.SKIPPED: "Écarté", queue.CANCELLED: "Annulé"}  # fmt: skip
KINDS = {"mail": "détails dans le mail", "bloque": "mail refusé", "sans_mail": "sans adresse mail",
         "relance_bloque": "refus repéré après coup"}  # fmt: skip
WRONG_LIMIT = f"Indiquez un nombre de mails par jour entre 1 et {MAX_LIMIT}."


class InvalidLimit(ValueError):
    """Plafond refusé ; le message dit quoi saisir."""


@dataclass(frozen=True)
class QueueLine:
    queue_id: int
    name: str
    status: str
    label: str
    reason: str | None
    at: datetime


@dataclass(frozen=True)
class QueueScreen:
    lines: list[QueueLine]
    paused: str | None
    limit: int
    sent_today: int
    sms: list[tuple[str, str, str | None, str | None]] = field(default_factory=list)  # C177


def queue_screen(engine: Engine, now: datetime, timezone: str) -> QueueScreen:
    with engine.connect() as conn:
        rows = queue.recent(conn, SHOWN)
        stop, limit = settings.paused(conn), settings.daily_limit(conn)
        today = queue.sent_since(conn, local_day_start(now, timezone))
        texts = recent_sms(conn, SHOWN)
    lines = [QueueLine(i, name, s, LABELS.get(s, s), reason, at) for i, name, s, reason, at in rows]
    sms = [(name, LABELS.get(s, s), KINDS.get(kind or "", kind), reason)
           for name, s, kind, reason in texts]  # fmt: skip
    return QueueScreen(lines, stop, limit, today, sms)


def cancel_line(engine: Engine, queue_id: int, now: datetime) -> None:
    """Le SMS qui attendait ce mail est annulé avec lui (C177)."""
    with engine.begin() as conn:
        prospect_id = queue.cancel(conn, queue_id, now)
        if prospect_id is not None:
            cancel_sms_after_mail(conn, prospect_id, now)


def resume(engine: Engine) -> None:
    with engine.begin() as conn:
        settings.set_paused(conn, None)


def change_limit(engine: Engine, text: str) -> None:
    """InvalidLimit si la saisie n'est pas un nombre de 1 à MAX_LIMIT."""
    try:
        limit = int(text.strip())
    except ValueError:
        raise InvalidLimit(WRONG_LIMIT) from None
    if not 1 <= limit <= MAX_LIMIT:
        raise InvalidLimit(WRONG_LIMIT)
    with engine.begin() as conn:
        settings.save_daily_limit(conn, limit)


def current_limit(engine: Engine) -> int:
    with engine.connect() as conn:
        return settings.daily_limit(conn)
