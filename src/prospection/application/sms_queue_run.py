"""Envoi des SMS par la tâche de fond (C177, C178) et reprise des STOP de Brevo (C180).

Un SMS part 20 minutes après le mail qu'il accompagne, ou tout de suite s'il est seul, aux
heures d'envoi et sous le plafond du jour. Juste avant, la conversation Gmail du mail est
relue : la version dit si le mail est parti, s'il a été refusé, ou qu'il n'y en a pas.
Brevo muet ou sans crédits : le même SMS est retenté 30 minutes plus tard.
"""

from datetime import datetime, timedelta

import httpx
from sqlalchemy import Connection, Engine

from prospection.application.api_keys import read_key
from prospection.application.audit_mail import REFUSED
from prospection.application.mail_material import mail_material
from prospection.application.mail_recipients import OPTED_OUT
from prospection.application.mail_replies import check_thread_of
from prospection.application.sms_eligibility import sms_target
from prospection.domain.send_pace import local_day_start, may_send
from prospection.domain.services import Service
from prospection.domain.sms_target import phone_fingerprint
from prospection.domain.sms_text import fill_sms
from prospection.sources.brevo import (
    BrevoNoCredits,
    BrevoRefused,
    BrevoUnavailable,
    send_sms,
    stop_numbers,
)
from prospection.sources.gmail import GmailOAuth
from prospection.storage import sms_queue_store as store
from prospection.storage.mail_outcome import mail_outcome
from prospection.storage.mail_settings import load_mail_settings
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox
from prospection.storage.sms_settings_store import load_sms_settings

RETRY, SYNC_EVERY, SYNC_RETRY = timedelta(minutes=30), timedelta(days=1), timedelta(hours=1)
NOTHING = "aucun point d'audit à citer"
REFUSED_BY_BREVO = "refusé par Brevo (numéro ou expéditeur)"


def _version(conn: Connection, prospect_id: int) -> str | None:
    """« mail », « bloque », « sans_mail », ou None : pas de SMS (désinscrit des mails)."""
    o = mail_outcome(conn, prospect_id)
    if o.bounced or (o.queue_status == "echec" and o.queue_reason == REFUSED):
        return "bloque"
    if o.sent:
        return "mail"
    return None if o.queue_reason == OPTED_OUT else "sans_mail"


def send_next_sms(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    now: datetime, tz: str,
) -> bool:  # fmt: skip
    """Envoie le prochain SMS prêt ; vrai si une ligne a été traitée."""
    key = read_key(engine, box, Service.BREVO)
    with engine.connect() as conn:
        settings, due = load_sms_settings(conn), store.next_due_sms(conn, now)
        today = store.sms_sent_since(conn, local_day_start(now, tz))
    if key is None or not settings.enabled or due is None:
        return False
    if not may_send(now, None, today, settings.daily_limit, tz):
        return False
    queue_id, prospect_id, forced = due
    if forced is None:
        check_thread_of(engine, box, client, oauth, prospect_id, now)  # refus arrivé depuis ?
    with engine.connect() as conn:
        prospect, my_phone = load_prospect(conn, prospect_id), load_mail_settings(conn).phone
        target = sms_target(conn, prospect, settings, True, my_phone, box.pepper, forced) \
            if prospect else None  # fmt: skip
        kind = forced or _version(conn, prospect_id)
    if prospect is None or target is None or target.reason or kind is None:
        why = target.reason if target else None
        return _done(engine, queue_id, "ecarte", why or OPTED_OUT, None, now)
    points = mail_material(engine, box, client, prospect, now).points
    if not points or not target.mobile or not target.phone_hash:
        return _done(engine, queue_id, "ecarte", NOTHING, None, now)
    name = str(prospect.data.get("name") or "")
    text = fill_sms(kind, name, points[0].title, my_phone or "")
    try:
        send_sms(client, key, settings.sender, target.mobile, text)
    except (BrevoUnavailable, BrevoNoCredits):
        with engine.begin() as conn:
            store.retry_later(conn, queue_id, kind, now + RETRY)
        return False
    except BrevoRefused:
        return _done(engine, queue_id, "echec", REFUSED_BY_BREVO, kind, now)
    with engine.begin() as conn:
        store.record_sms(conn, prospect_id, target.phone_hash, kind, now)
    return _done(engine, queue_id, "envoye", None, kind, now)


def _done(engine: Engine, queue_id: int, status: str, reason: str | None, kind: str | None,
          now: datetime) -> bool:  # fmt: skip
    with engine.begin() as conn:
        store.finish_sms(conn, queue_id, status, reason, kind, now)
    return True


def sync_stops(engine: Engine, box: SecretBox, client: httpx.Client, now: datetime) -> bool:
    """Une fois par jour, les numéros STOP de Brevo rejoignent la liste de refus (C180)."""
    key = read_key(engine, box, Service.BREVO)
    with engine.connect() as conn:
        synced = store.stops_synced_at(conn)
    if key is None or (synced is not None and now - synced < SYNC_EVERY):
        return False
    try:
        numbers = stop_numbers(client, key)
    except BrevoUnavailable:  # réessayé dans une heure
        with engine.begin() as conn:
            store.mark_stops_synced(conn, now - SYNC_EVERY + SYNC_RETRY)
        return False
    with engine.begin() as conn:
        store.add_stops(conn, [phone_fingerprint(n, box.pepper) for n in numbers], now)
        store.mark_stops_synced(conn, now)
    return True
