"""Page « Envois » (C169, C170) : la file du mail d'audit, son plafond, son arrêt."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.send_pace import local_day_start
from prospection.storage import mail_queue as queue
from prospection.storage import mail_queue_settings as settings

SHOWN = 200
MAX_LIMIT = 200
LABELS = {queue.WAITING: "En attente", queue.SENT: "Envoyé", queue.FAILED: "Échec",
          queue.SKIPPED: "Écarté", queue.CANCELLED: "Annulé"}  # fmt: skip
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


def queue_screen(engine: Engine, now: datetime, timezone: str) -> QueueScreen:
    with engine.connect() as conn:
        rows = queue.recent(conn, SHOWN)
        stop, limit = settings.paused(conn), settings.daily_limit(conn)
        today = queue.sent_since(conn, local_day_start(now, timezone))
    lines = [QueueLine(i, name, s, LABELS.get(s, s), reason, at) for i, name, s, reason, at in rows]
    return QueueScreen(lines, stop, limit, today)


def cancel_line(engine: Engine, queue_id: int, now: datetime) -> None:
    with engine.begin() as conn:
        queue.cancel(conn, queue_id, now)


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
