"""C108, C77, C76, C98 : règles pures du suivi dans le temps."""

import dataclasses
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from prospection.domain.place_changes import place_changes
from prospection.domain.reminders import reminder_due
from prospection.domain.schedule import next_run
from prospection.domain.stop_reasons import budget_reached, exhausted, goal_reached, is_failure
from tests.storage.test_campaigns import PLACE

PARIS = ZoneInfo("Europe/Paris")
DAY = date(2026, 10, 28)


def at(hour: int, minute: int = 0, day: int = 28) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=PARIS)


def test_C108_timed_action_reminded_15_minutes_before() -> None:
    call = time(14, 30)
    assert not reminder_due(DAY, call, at(14, 14))
    assert reminder_due(DAY, call, at(14, 15))
    assert reminder_due(DAY, call, at(14, 40))  # tâche de fond en retard : encore utile
    assert not reminder_due(DAY, call, at(17))
    assert reminder_due(DAY, call, at(13, 30), lead_minutes=60)  # réglable


def test_C108_untimed_action_reminded_at_8_in_the_morning() -> None:
    assert not reminder_due(DAY, None, at(7, 59))
    assert reminder_due(DAY, None, at(8))
    assert reminder_due(DAY, None, at(7), morning_hour=7)  # réglable
    assert not reminder_due(DAY, None, at(9, day=29))  # la veille : déjà « en retard »


def test_C77_next_run_every_week_in_my_time_zone() -> None:
    wednesday = at(10)
    assert next_run(wednesday, 0, 7) == datetime(2026, 11, 2, 7, tzinfo=PARIS)  # lundi
    assert next_run(wednesday, 2, 11) == at(11)  # plus tard aujourd'hui
    assert next_run(wednesday, 2, 10) == datetime(2026, 11, 4, 10, tzinfo=PARIS)  # pas deux fois
    before_dst = datetime(2026, 10, 20, 9, tzinfo=PARIS)  # heure d'été
    assert next_run(before_dst, 0, 7).hour == 7  # 26/10 : heure d'hiver, toujours 7 h


def test_C76_changes_of_a_place_in_plain_words() -> None:
    old = dataclasses.replace(PLACE, website="https://atelier.fr")
    closed = dataclasses.replace(old, business_status="CLOSED_PERMANENTLY", website=None)
    assert place_changes(old, closed) == ["Fermé définitivement", "Site supprimé"]
    moved = dataclasses.replace(old, website="https://neuf.fr", phone="+33400000000")
    assert place_changes(old, moved) == ["Site changé", "Téléphone changé"]
    assert place_changes(PLACE, dataclasses.replace(PLACE, website="https://a.fr")) == [
        "Site ajouté"
    ]
    assert place_changes(closed, old) == ["Rouvert", "Site ajouté"]
    assert place_changes(old, dataclasses.replace(old, rating=4.9)) == []
    spaced = dataclasses.replace(old, phone="+33 6 12 34 56 78")  # même numéro, autre écriture
    assert place_changes(old, spaced) == []


def test_C98_failure_is_anything_but_goal_or_exhausted_source() -> None:
    assert not is_failure(goal_reached(3)) and not is_failure(exhausted(1, 3))
    assert not is_failure(exhausted(0, 3, registry_only=True))
    assert is_failure(budget_reached(0, 1, 3))
    assert is_failure("Clé Google absente ou illisible : ajoutez-la.") and is_failure(None)
