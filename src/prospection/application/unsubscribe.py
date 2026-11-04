"""Désinscription du mail d'audit, depuis le lien du mail (C148).

Jeton aléatoire de l'envoi (impossible à deviner) ; l'adresse est bloquée pour toujours,
seule son empreinte est gardée.
"""

import re
from datetime import datetime

from sqlalchemy import Engine

from prospection.storage.audit_mails import opt_out

_TOKEN = re.compile(r"[A-Za-z0-9_-]{16,64}")


def unsubscribe(engine: Engine, token: str, now: datetime) -> bool:
    """Faux si le lien est inconnu."""
    if not _TOKEN.fullmatch(token):
        return False
    with engine.begin() as conn:
        return opt_out(conn, token, now)
