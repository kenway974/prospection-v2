"""Envoi des SMS par la tâche de fond (C177, C178) et reprise des STOP de Brevo (C180).

Un SMS part 20 minutes après le mail qu'il accompagne, ou tout de suite s'il est seul, aux
heures d'envoi, sous le plafond du jour, une minute au moins après le précédent, par un seul
envoyeur à la fois. Juste avant, la conversation Gmail du mail est relue : la version dit si
le mail est parti, s'il a été refusé, ou qu'il n'y en a pas. Le SMS est réservé avant
l'appel à Brevo : une réponse perdue ne le fait jamais partir deux fois. Brevo injoignable ou
sans crédits : nouvel essai 30 minutes plus tard, la version étant choisie à nouveau.
"""

import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.application.mail_material import mail_material
from prospection.application.mail_replies import check_thread_of
from prospection.application.sms_eligibility import FOLLOW_UP, sms_target
from prospection.application.sms_version import sms_version
from prospection.domain.send_pace import local_day_start, may_send
from prospection.domain.services import Service
from prospection.domain.sms_settings import SmsSettings
from prospection.domain.sms_target import phone_fingerprint
from prospection.domain.sms_text import fill_sms
from prospection.sources.brevo import (
    BrevoNoCredits,
    BrevoRefused,
    BrevoUnavailable,
    BrevoUncertain,
    send_sms,
    stop_numbers,
)
from prospection.sources.gmail import GmailOAuth
from prospection.storage import sms_queue_store as store
from prospection.storage.mail_settings import load_mail_settings
from prospection.storage.prospect_list import load_prospect
from prospection.storage.secret_box import SecretBox
from prospection.storage.send_lock import SMS_LOCK, single_sender
from prospection.storage.sms_settings_store import load_sms_settings

RETRY, SYNC_EVERY, SYNC_RETRY = timedelta(minutes=30), timedelta(days=1), timedelta(hours=1)
GAP_SECONDS, MAX_STOP_DAYS = 60, 90
NOTHING, UNCERTAIN = "aucun point d'audit à citer", "envoi incertain (réponse de Brevo perdue)"
REFUSED_BY_BREVO, BROKEN = "refusé par Brevo (numéro ou expéditeur)", "erreur imprévue (journal)"
logger = logging.getLogger(__name__)


def send_next_sms(
    engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
    now: datetime, tz: str,
) -> bool:  # fmt: skip
    """Envoie le prochain SMS prêt ; vrai si une ligne a été traitée."""
    key = read_key(engine, box, Service.BREVO)
    with engine.connect() as conn:
        settings, due = load_sms_settings(conn), store.next_due_sms(conn, now)
        today = store.sms_sent_since(conn, local_day_start(now, tz))
        last = store.last_sms_at(conn)
    pace = (last, GAP_SECONDS) if last else None
    if key is None or not settings.enabled or due is None:
        return False
    if not may_send(now, pace, today, settings.daily_limit, tz):
        return False
    with single_sender(engine, SMS_LOCK) as alone:
        if not alone:
            return False
        try:
            return _send(engine, box, client, oauth, now, key, settings, due)
        except Exception:  # donnée imprévue : la ligne est close, jamais rejouée en boucle
            logger.exception("SMS impossible à préparer")
            return _done(engine, due[0], "echec", BROKEN, None, now)


def _send(engine: Engine, box: SecretBox, client: httpx.Client, oauth: GmailOAuth | None,
          now: datetime, key: str, settings: SmsSettings, due: tuple[int, int, str | None]
          ) -> bool:  # fmt: skip
    queue_id, prospect_id, forced = due
    if forced is None:
        check_thread_of(engine, box, client, oauth, prospect_id, now)  # refus arrivé depuis ?
    with engine.connect() as conn:
        prospect, my_phone = load_prospect(conn, prospect_id), load_mail_settings(conn).phone
        target = (sms_target(conn, prospect, settings, True, my_phone, box.pepper, forced)
                  if prospect else None)  # fmt: skip
        kind = forced or sms_version(conn, prospect_id)
    if prospect is None or target is None or target.reason or kind is None:
        return _done(engine, queue_id, "ecarte", target.reason if target else None, None, now)
    points = mail_material(engine, box, client, prospect, now).points
    if not points or not target.mobile or not target.phone_hash:
        return _done(engine, queue_id, "ecarte", NOTHING, None, now)
    text = fill_sms(kind, str(prospect.data.get("name") or ""), points[0].code, my_phone or "")
    with engine.begin() as conn:
        reserved = store.record_sms(conn, prospect_id, target.phone_hash, kind, now)
    try:
        send_sms(client, key, settings.sender, target.mobile, text)
    except BrevoUncertain:
        return _done(engine, queue_id, "envoye", UNCERTAIN, kind, now)
    except (BrevoUnavailable, BrevoNoCredits, BrevoRefused) as error:
        with engine.begin() as conn:
            store.unrecord_sms(conn, reserved)
            if isinstance(error, BrevoRefused):
                store.finish_sms(conn, queue_id, "echec", REFUSED_BY_BREVO, kind, now)
                return True
            store.retry_later(conn, queue_id, kind if kind == FOLLOW_UP else None, now + RETRY)
        return False
    return _done(engine, queue_id, "envoye", None, kind, now)


def _done(engine: Engine, queue_id: int, status: str, reason: str | None, kind: str | None,
          now: datetime) -> bool:  # fmt: skip
    with engine.begin() as conn:
        store.finish_sms(conn, queue_id, status, reason, kind, now)
    return True


def sync_stops(engine: Engine, box: SecretBox, client: httpx.Client, now: datetime) -> bool:
    """Une fois par jour, les numéros STOP de Brevo rejoignent la liste de refus (C180), en
    remontant jusqu'à la dernière reprise (même après des jours d'arrêt)."""
    key = read_key(engine, box, Service.BREVO)
    with engine.connect() as conn:
        synced = store.stops_synced_at(conn)
    if key is None or (synced is not None and now - synced < SYNC_EVERY):
        return False
    days = min(MAX_STOP_DAYS, (now - synced).days + 2) if synced else MAX_STOP_DAYS
    try:
        numbers = stop_numbers(client, key, days)
    except BrevoUnavailable:  # réessayé dans une heure
        with engine.begin() as conn:
            store.mark_stops_synced(conn, now - SYNC_EVERY + SYNC_RETRY)
        return False
    with engine.begin() as conn:
        store.add_stops(conn, [phone_fingerprint(n, box.pepper) for n in numbers], now)
        store.mark_stops_synced(conn, now)
    return True
