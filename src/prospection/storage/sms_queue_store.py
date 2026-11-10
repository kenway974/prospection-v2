"""File des SMS, SMS envoyés, numéros STOP (C176 à C180)."""

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import Connection, func, select, true, update
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.mail_queue import WAITING, mail_queue
from prospection.storage.sms_tables import sms_optouts, sms_queue, sms_sends, sms_settings

AFTER_MAIL = timedelta(minutes=20)  # la plupart des refus de mail arrivent avant (C177)
_Q, _S, _M = sms_queue.c, sms_sends.c, mail_queue.c


def enqueue_sms(conn: Connection, rows: Sequence[tuple[int, bool]], now: datetime,
                kind: str | None = None) -> int:  # fmt: skip
    """`rows` : (prospect, attend le mail de la file) ; `kind` imposé (relance, C178)."""
    if not rows:
        return 0
    values = [{"prospect_id": p, "queued_at": now, "after_mail": after,
               "due_at": None if after else now, "kind": kind} for p, after in rows]  # fmt: skip
    added = conn.execute(
        insert(sms_queue).values(values)
        .on_conflict_do_nothing(index_elements=["prospect_id"], index_where=_Q.status == WAITING)
        .returning(_Q.id)
    )  # fmt: skip
    return len(added.all())


def next_due_sms(conn: Connection, now: datetime) -> tuple[int, int, str | None] | None:
    """(ligne, prospect, version imposée) du plus ancien SMS prêt à partir : son heure est
    venue, ou le mail qu'il attend est traité depuis 20 minutes."""
    mail = (
        select(_M.status, _M.done_at).where(_M.prospect_id == _Q.prospect_id)
        .order_by(_M.id.desc()).limit(1).lateral()
    )  # fmt: skip
    ready_alone = (~_Q.after_mail) & (_Q.due_at <= now)
    ready_after = _Q.after_mail & (mail.c.status != WAITING) & (mail.c.done_at <= now - AFTER_MAIL)
    found = (
        select(_Q.id, _Q.prospect_id, _Q.kind).select_from(sms_queue.outerjoin(mail, true()))
        .where(_Q.status == WAITING, ready_alone | ready_after)
        .order_by(_Q.queued_at, _Q.id).limit(1)
    )  # fmt: skip
    row = conn.execute(found).first()
    return (int(row.id), int(row.prospect_id), row.kind) if row else None


def finish_sms(conn: Connection, queue_id: int, status: str, reason: str | None,
               kind: str | None, now: datetime) -> None:  # fmt: skip
    conn.execute(update(sms_queue).where(_Q.id == queue_id).values(
        status=status, reason=reason, kind=kind, done_at=now))  # fmt: skip


def retry_later(conn: Connection, queue_id: int, kind: str, when: datetime) -> None:
    """Brevo muet ou sans crédits : même version, plus tard, sans attendre de mail."""
    conn.execute(update(sms_queue).where(_Q.id == queue_id).values(
        kind=kind, after_mail=False, due_at=when))  # fmt: skip


def cancel_sms_after_mail(conn: Connection, prospect_id: int, now: datetime) -> None:
    """Le mail annulé emporte le SMS qui l'attendait."""
    conn.execute(update(sms_queue).where(
        _Q.prospect_id == prospect_id, _Q.status == WAITING, _Q.after_mail
    ).values(status="annule", done_at=now))  # fmt: skip


def record_sms(conn: Connection, prospect_id: int, phone_hash: str, kind: str,
               now: datetime) -> None:  # fmt: skip
    conn.execute(sms_sends.insert().values(prospect_id=prospect_id, phone_hash=phone_hash,
                                           kind=kind, sent_at=now))  # fmt: skip


def sms_kinds_sent(conn: Connection, prospect_id: int, phone_hash: str) -> set[str]:
    """Versions déjà reçues par ce prospect ou ce numéro."""
    found = select(_S.kind).where((_S.prospect_id == prospect_id) | (_S.phone_hash == phone_hash))
    return set(conn.execute(found).scalars())


def sms_sent_since(conn: Connection, start: datetime) -> int:
    return int(conn.execute(select(func.count()).where(_S.sent_at >= start)).scalar_one())


def is_stopped(conn: Connection, phone_hash: str) -> bool:
    found = select(sms_optouts.c.phone_hash).where(sms_optouts.c.phone_hash == phone_hash)
    return conn.execute(found).first() is not None


def add_stops(conn: Connection, hashes: Sequence[str], now: datetime) -> None:
    if hashes:
        conn.execute(insert(sms_optouts).values(
            [{"phone_hash": h, "created_at": now} for h in set(hashes)]
        ).on_conflict_do_nothing())  # fmt: skip


def stops_synced_at(conn: Connection) -> datetime | None:
    return conn.execute(select(sms_settings.c.optouts_synced_at)).scalar()


def mark_stops_synced(conn: Connection, now: datetime) -> None:
    conn.execute(update(sms_settings).values(optouts_synced_at=now))


def sms_waiting(conn: Connection, prospect_id: int) -> bool:
    found = select(_Q.id).where(_Q.prospect_id == prospect_id, _Q.status == WAITING)
    return conn.execute(found).first() is not None


def recent_sms(conn: Connection, limit: int) -> list[tuple[str, str, str | None, str | None]]:
    """(entreprise, statut, version, raison) : en attente d'abord, puis les derniers (C177)."""
    from prospection.storage.schema_campaigns import prospects

    name = prospects.c.data_json["name"].astext
    found = (
        select(name.label("name"), _Q.status, _Q.kind, _Q.reason, _Q.after_mail)
        .join(prospects, prospects.c.id == _Q.prospect_id)
        .order_by((_Q.status != WAITING).asc(), func.coalesce(_Q.done_at, _Q.queued_at).desc())
        .limit(limit)
    )  # fmt: skip
    return [(str(r.name or ""), r.status, r.kind or ("après le mail" if r.after_mail else None),
             r.reason) for r in conn.execute(found)]  # fmt: skip
