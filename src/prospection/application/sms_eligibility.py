"""Ce prospect peut-il recevoir le SMS (C176) ? Mobile français, SMS activés avec une clé
Brevo, jamais un entrepreneur non diffusible, jamais après un STOP, une seule fois."""

from dataclasses import dataclass

from sqlalchemy import Connection

from prospection.domain.company_card import NON_DIFFUSIBLE
from prospection.domain.sms_settings import SmsSettings
from prospection.domain.sms_target import french_mobile, phone_fingerprint
from prospection.storage.prospect_list import ProspectRow
from prospection.storage.sms_queue_store import is_stopped, sms_kinds_sent

OFF, NO_KEY = "SMS désactivés (Réglages → SMS)", "clé Brevo manquante (Réglages → Clés)"
NO_PHONE = "votre numéro manque (Réglages → Mail d'audit)"
PRIVATE, NO_MOBILE = "entrepreneur non diffusible", "pas de mobile"
STOPPED, ALREADY = "a répondu STOP", "SMS déjà envoyé"
FOLLOW_UP = "relance_bloque"  # C178 : seule version permise après un premier SMS


@dataclass(frozen=True)
class SmsTarget:
    mobile: str | None
    phone_hash: str | None
    reason: str | None  # None : le SMS peut partir


def mobile_of(prospect: ProspectRow) -> str | None:
    site = prospect.site.contacts.phones if prospect.site and prospect.site.contacts else ()
    numbers = [prospect.contact[1] or "", str(prospect.data.get("phone") or ""), *site]
    return french_mobile(n for n in numbers if n)


def sms_target(
    conn: Connection, prospect: ProspectRow, settings: SmsSettings, has_key: bool,
    my_phone: str | None, pepper: bytes, kind: str | None = None,
) -> SmsTarget:  # fmt: skip
    mobile = mobile_of(prospect)
    print_ = phone_fingerprint(mobile, pepper) if mobile else None
    sent = sms_kinds_sent(conn, prospect.id, print_) if print_ else set()
    allowed_again = kind == FOLLOW_UP and FOLLOW_UP not in sent
    checks = [
        (not settings.enabled, OFF), (not has_key, NO_KEY), (not my_phone, NO_PHONE),
        (prospect.registry_status == NON_DIFFUSIBLE, PRIVATE), (print_ is None, NO_MOBILE),
        (print_ is not None and is_stopped(conn, print_), STOPPED),
        (bool(sent) and not allowed_again, ALREADY),
    ]  # fmt: skip
    reason = next((why for failed, why in checks if failed), None)
    return SmsTarget(mobile, print_, reason)
