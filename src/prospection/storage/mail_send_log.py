"""Journal des mails d'audit pour les statistiques et la détection des réponses (C162 à C164)."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Connection, or_, select, update

from prospection.storage.audit_mails import mail_sends
from prospection.storage.schema_campaigns import prospects

_S = mail_sends.c
WATCH_DAYS, RECHECK = 30, timedelta(hours=6)  # réponses cherchées 30 jours, toutes les 6 h


@dataclass(frozen=True)
class SentMail:
    prospect_id: int | None
    subject_version: str | None
    hook_version: str | None
    structure: str | None
    edited: bool | None
    points: tuple[str, ...]
    profile: dict[str, str]
    replied: bool
    bounced: bool
    status: str | None  # résultat d'appel du prospect (None : prospect supprimé)
    thread_id: str | None = None


def all_sends(conn: Connection) -> list[SentMail]:
    p = prospects.c
    rows = conn.execute(
        select(_S.prospect_id, _S.subject_version, _S.hook_version, _S.structure, _S.edited,
               _S.points, _S.profile, _S.replied_at, _S.bounced_at, p.status, _S.thread_id)
        .select_from(mail_sends.outerjoin(prospects, p.id == _S.prospect_id))
        .order_by(_S.sent_at, _S.id)
    )  # fmt: skip
    return [
        SentMail(
            r.prospect_id,
            r.subject_version,
            r.hook_version,
            r.structure,
            r.edited,
            tuple(r.points or ()),
            dict(r.profile or {}),
            r.replied_at is not None,
            r.bounced_at is not None,
            r.status,
            r.thread_id,
        )
        for r in rows
    ]


def version_counts(conn: Connection) -> dict[str, dict[str, int]]:
    """Nombre d'envois par version : objet, accroche, structure (C162)."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in conn.execute(select(_S.subject_version, _S.hook_version, _S.structure)):
        for kind, value in (("subject", r.subject_version), ("hook", r.hook_version),
                            ("structure", r.structure)):  # fmt: skip
            if value:
                counts[kind][value] += 1
    return counts


def set_thread(conn: Connection, token: str, thread_id: str | None) -> None:
    conn.execute(update(mail_sends).where(_S.token == token).values(thread_id=thread_id))


def replies_to_check(conn: Connection, now: datetime, limit: int) -> list[tuple[int, int, str]]:
    """(envoi, prospect, conversation) sans réponse, envoyés depuis moins de 30 jours."""
    rows = conn.execute(
        select(_S.id, _S.prospect_id, _S.thread_id)
        .where(_S.thread_id.is_not(None), _S.replied_at.is_(None), _S.bounced_at.is_(None),
               _S.prospect_id.is_not(None), _S.sent_at > now - timedelta(days=WATCH_DAYS),
               or_(_S.reply_checked_at.is_(None), _S.reply_checked_at < now - RECHECK))
        .order_by(_S.reply_checked_at.nulls_first(), _S.id).limit(limit)
    )  # fmt: skip
    return [(int(r.id), int(r.prospect_id), str(r.thread_id)) for r in rows]


def mark_checked(conn: Connection, send_id: int, now: datetime, replied: bool) -> None:
    values: dict[str, object] = {"reply_checked_at": now}
    if replied:
        values["replied_at"] = now
    conn.execute(update(mail_sends).where(_S.id == send_id).values(**values))
