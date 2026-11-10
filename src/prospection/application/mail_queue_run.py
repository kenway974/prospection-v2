"""Envoi de la file du mail d'audit par la tâche de fond (C169, C170), sans relecture.

Un envoi à la fois, au rythme de `send_pace`. Tout est revérifié au moment d'envoyer. Ce qui
bloque toute la file (Gmail délié, réglages manquants, trois refus de Gmail de suite) l'arrête
et le dit ; ce qui ne concerne qu'un prospect l'écarte, avec sa raison.
"""

import random
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.audit_mail import (
    DOWN,
    REFUSED,
    REVOKED,
    UNCERTAIN,
    MailBlocked,
    send_audit_mail,
)
from prospection.application.audit_mail_context import (
    GMAIL,
    NO_BASE,
    SETTINGS,
    draft_for,
    load_context,
)
from prospection.application.mail_batch import batch_row
from prospection.domain.send_pace import local_day_start, may_send, next_gap
from prospection.sources.gmail import GmailOAuth
from prospection.storage import mail_queue as queue
from prospection.storage.mail_queue_settings import daily_limit, paused, set_paused
from prospection.storage.secret_box import SecretBox

STOP_AFTER = 3  # refus de Gmail de suite
WHOLE_QUEUE = (SETTINGS, GMAIL, NO_BASE, REVOKED)  # rien ne peut partir tant que ce n'est pas réglé
STOPPED = "File arrêtée après 3 refus de Gmail de suite ({raison}). Vérifiez, puis reprenez."


def _due(engine: Engine, now: datetime, tz: str) -> tuple[int, int] | None:
    """Ligne à traiter maintenant, ou None (file vide, arrêtée, hors rythme)."""
    with engine.connect() as conn:
        if paused(conn) or (found := queue.next_waiting(conn)) is None:
            return None
        sent = queue.sent_since(conn, local_day_start(now, tz))
        ready = may_send(now, queue.last_attempt(conn), sent, daily_limit(conn), tz)
    return found if ready else None


def send_next(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    base: str | None, now: datetime, tz: str, rng: random.Random,
) -> bool:  # fmt: skip
    """Traite le prochain prospect de la file ; vrai si une ligne a été traitée."""
    due = _due(engine, now, tz)
    if due is None:
        return False
    queue_id, prospect_id = due
    with engine.connect() as conn:
        row = batch_row(conn, prospect_id, box.pepper, set())
    if row is None or row.reason:
        return _finish(engine, queue_id, queue.SKIPPED, row.reason if row else None, now, None)
    ctx = load_context(engine, box, client, oauth, base, prospect_id, now)
    draft = draft_for(ctx, None)
    if ctx.blocked in WHOLE_QUEUE or (ctx.blocked is None and draft is None):
        with engine.begin() as conn:
            set_paused(conn, ctx.blocked or SETTINGS)
        return False
    if ctx.blocked or draft is None:
        return _finish(engine, queue_id, queue.SKIPPED, ctx.blocked, now, None)
    status, reason = queue.SENT, None
    try:
        send_audit_mail(engine, box, client, oauth, base, prospect_id, ctx.recipients[0],
                        draft.subject, draft.body, now, tz, ctx.versions)  # fmt: skip
    except MailBlocked as blocked:
        reason = str(blocked)
        status = queue.SENT if reason == UNCERTAIN else (
            queue.FAILED if reason in (DOWN, REFUSED, REVOKED) else queue.SKIPPED)  # fmt: skip
    _finish(engine, queue_id, status, reason, now, next_gap(rng))
    if status == queue.FAILED:
        _stop_if_stuck(engine, reason or "")
    return True


def _finish(engine: Engine, queue_id: int, status: str, reason: str | None, now: datetime,
            gap: int | None) -> bool:  # fmt: skip
    with engine.begin() as conn:
        queue.finish(conn, queue_id, status, reason, now, gap)
    return True


def _stop_if_stuck(engine: Engine, reason: str) -> None:
    with engine.begin() as conn:
        if queue.last_attempts(conn, STOP_AFTER) == [queue.FAILED] * STOP_AFTER:
            set_paused(conn, STOPPED.format(raison=reason.rstrip(".")))
