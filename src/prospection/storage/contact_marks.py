"""Où en est le contact de chaque prospect (C184) : mail envoyé, refusé, en file, SMS."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Connection, select

from prospection.storage.audit_mails import mail_sends
from prospection.storage.mail_queue import WAITING, mail_queue
from prospection.storage.sms_tables import sms_sends

Mark = tuple[str, datetime | None]  # « envoye », « refuse », « file », « sms » ; date


def contact_marks(conn: Connection, prospect_ids: Sequence[int]) -> dict[int, Mark]:
    """Le plus parlant d'abord : refusé, puis envoyé, puis en file, puis SMS seul."""
    if not prospect_ids:
        return {}
    marks: dict[int, Mark] = {}
    s, q, t = mail_sends.c, mail_queue.c, sms_sends.c
    for pid, at in conn.execute(
        select(t.prospect_id, t.sent_at).where(t.prospect_id.in_(prospect_ids))
    ):
        marks[int(pid)] = ("sms", at)
    waiting = select(q.prospect_id).where(q.prospect_id.in_(prospect_ids), q.status == WAITING)
    for pid in conn.execute(waiting).scalars():
        marks[int(pid)] = ("file", None)
    sends = select(s.prospect_id, s.sent_at, s.bounced_at).where(s.prospect_id.in_(prospect_ids))
    for pid, sent, bounced in conn.execute(sends.order_by(s.sent_at)):
        marks[int(pid)] = ("refuse", bounced) if bounced else ("envoye", sent)
    return marks
