"""RGPD : quels prospects purger (C94) et trace d'une suppression demandée (C95)."""

import hashlib
from calendar import monthrange
from datetime import datetime

from prospection.domain.call_status import TO_CALL

# Jamais purgés : intéressé, exporté, à rappeler, ni un prospect avec une action ouverte.
PURGEABLE = frozenset({TO_CALL, "pas intéressé", "messagerie", "pas joint", "faux numéro"})
ERASED_REASON = "Suppression demandée (RGPD)"


def purge_cutoff(now: datetime, months: int) -> datetime:
    """Même jour `months` mois plus tôt (dernier jour du mois s'il n'existe pas)."""
    total = now.year * 12 + now.month - 1 - months
    year, month = divmod(total, 12)
    day = min(now.day, monthrange(year, month + 1)[1])
    return now.replace(year=year, month=month + 1, day=day)


def erasure_key(identifier: str) -> str:
    """Empreinte d'un identifiant (fiche Google, « siren:… ») : l'entreprise n'est plus jamais
    reprise, sans garder son identifiant lisible."""
    return hashlib.sha256(f"prospection-effacement:{identifier}".encode()).hexdigest()
