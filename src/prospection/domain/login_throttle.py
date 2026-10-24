"""Limite d'essais de connexion (C82) : 5 échecs en 15 min bloquent 15 min."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
LOCKOUT = timedelta(minutes=15)


@dataclass(frozen=True)
class Throttle:
    allowed: bool
    retry_after: timedelta


def check_login_allowed(failures: Sequence[datetime], now: datetime) -> Throttle:
    """Décide si une tentative est permise, à partir des dates des échecs."""
    recent = [at for at in failures if now - WINDOW <= at <= now]
    if len(recent) < MAX_FAILURES:
        return Throttle(allowed=True, retry_after=timedelta(0))
    wait = max(recent) + LOCKOUT - now
    if wait <= timedelta(0):
        return Throttle(allowed=True, retry_after=timedelta(0))
    minutes = math.ceil(wait.total_seconds() / 60)
    return Throttle(allowed=False, retry_after=timedelta(minutes=minutes))
