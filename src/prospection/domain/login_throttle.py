"""Limite d'essais de connexion (C82).

Par IP : 5 échecs en 15 min bloquent cette IP 15 min. Un inconnu ne peut donc
pas bloquer le propriétaire depuis une autre adresse.
Pour toutes les IP : 50 échecs en 15 min bloquent tout le monde 15 min
(attaque répartie sur de nombreuses adresses).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

MAX_FAILURES_PER_IP = 5
MAX_FAILURES_ALL_IPS = 50
WINDOW = timedelta(minutes=15)
LOCKOUT = timedelta(minutes=15)


@dataclass(frozen=True)
class Throttle:
    allowed: bool
    retry_after: timedelta


def _wait(failures: Sequence[datetime], limit: int, now: datetime) -> timedelta:
    recent = [at for at in failures if now - WINDOW <= at <= now]
    if len(recent) < limit:
        return timedelta(0)
    return max(recent) + LOCKOUT - now


def check_login_allowed(
    ip_failures: Sequence[datetime], all_failures: Sequence[datetime], now: datetime
) -> Throttle:
    """Décide si une tentative est permise, à partir des dates des échecs."""
    wait = max(
        _wait(ip_failures, MAX_FAILURES_PER_IP, now),
        _wait(all_failures, MAX_FAILURES_ALL_IPS, now),
    )
    if wait <= timedelta(0):
        return Throttle(allowed=True, retry_after=timedelta(0))
    minutes = math.ceil(wait.total_seconds() / 60)
    return Throttle(allowed=False, retry_after=timedelta(minutes=minutes))
