"""C169 : rythme de l'envoi groupé : heures ouvrées, 60 à 120 s entre deux envois, plafond
par jour (heure de Paris)."""

import random
from datetime import UTC, datetime, timedelta

from prospection.domain.send_pace import GAP_MAX, GAP_MIN, may_send, next_gap

TZ = "Europe/Paris"
TUESDAY_10H = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)  # 10 h à Paris


def test_C169_only_on_working_days_and_hours() -> None:
    assert may_send(TUESDAY_10H, None, 0, 30, TZ)
    assert not may_send(TUESDAY_10H.replace(hour=7, minute=59), None, 0, 30, TZ)  # 8 h 59
    assert may_send(TUESDAY_10H.replace(hour=17, minute=59), None, 0, 30, TZ)  # 18 h 59
    assert not may_send(TUESDAY_10H.replace(hour=18), None, 0, 30, TZ)  # 19 h
    assert not may_send(TUESDAY_10H + timedelta(days=4), None, 0, 30, TZ)  # samedi


def test_C169_waits_the_random_gap_after_the_last_send() -> None:
    last = TUESDAY_10H - timedelta(seconds=70)
    assert not may_send(TUESDAY_10H, (last, 90), 0, 30, TZ)
    assert may_send(TUESDAY_10H, (last, 60), 0, 30, TZ)


def test_C169_daily_limit() -> None:
    assert not may_send(TUESDAY_10H, None, 30, 30, TZ)
    assert may_send(TUESDAY_10H, None, 29, 30, TZ)


def test_C169_gap_between_one_and_two_minutes() -> None:
    rng = random.Random(1)  # noqa: S311 (tirage rejouable du test)
    gaps = {next_gap(rng) for _ in range(200)}
    assert min(gaps) >= GAP_MIN == 60 and max(gaps) <= GAP_MAX == 120 and len(gaps) > 20


def test_C169_never_on_french_public_holidays() -> None:
    """Relecture : pas d'envoi commercial un jour férié (11 novembre, lundi de Pâques…)."""
    armistice = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)  # mercredi
    easter_monday = datetime(2027, 3, 29, 9, 0, tzinfo=UTC)
    ascension = datetime(2026, 5, 14, 9, 0, tzinfo=UTC)
    for day in (armistice, easter_monday, ascension):
        assert not may_send(day, None, 0, 30, TZ), day
    assert may_send(datetime(2026, 11, 12, 9, 0, tzinfo=UTC), None, 0, 30, TZ)
