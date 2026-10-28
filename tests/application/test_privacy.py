"""C94, C95 : purge des non retenus et suppression d'une entreprise sur demande."""

import dataclasses
from datetime import timedelta

import pytest
from sqlalchemy import Engine

from prospection.application.call_actions import record_result, save_note, schedule
from prospection.application.privacy import (
    InvalidPurge,
    change_purge_months,
    erase_company,
    purge,
)
from prospection.domain.criteria import Verdict
from prospection.domain.place import Place
from prospection.storage.alerts import add_alert, unseen_alerts
from prospection.storage.exclusions import load_exclusions
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import PARIS, add
from tests.storage.test_campaigns import PLACE

LATER = NOW + timedelta(days=200)  # plus de 6 mois


def _place(n: int) -> Place:
    return dataclasses.replace(PLACE, place_id=f"p{n}", name=f"Commerce {n}")


def _ids(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        return set(conn.exec_driver_sql("SELECT place_id FROM prospects").scalars())


def test_C94_only_inactive_and_not_kept_prospects_are_purged(campaign_db: Engine) -> None:
    to_call, refused, interested, callback, noted = add(campaign_db, *(_place(n) for n in range(5)))
    with campaign_db.begin() as conn:
        insert_prospect(conn, 1, _place(9), "x", Verdict(False, ("Avec site",), ()), NOW)
    record_result(campaign_db, refused, "pas intéressé", NOW)
    record_result(campaign_db, interested, "intéressé", NOW)
    record_result(campaign_db, callback, "pas joint", NOW)
    schedule(campaign_db, callback, "rappeler", "2027-06-01", "", NOW, PARIS)  # action ouverte
    record_result(campaign_db, noted, "messagerie", NOW)
    save_note(campaign_db, noted, "Rappeler en juin", LATER - timedelta(days=10))  # activité
    assert purge(campaign_db, NOW + timedelta(days=150)) == 0  # moins de 6 mois
    assert purge(campaign_db, LATER) == 3
    assert _ids(campaign_db) == {"p2", "p3", "p4"}
    assert to_call  # à appeler jamais appelé, exclu, pas intéressé : purgés


def test_C94_duration_is_adjustable(campaign_db: Engine) -> None:
    add(campaign_db, _place(1))
    change_purge_months(campaign_db, "12")
    assert purge(campaign_db, LATER) == 0
    with pytest.raises(InvalidPurge):
        change_purge_months(campaign_db, "0")


def test_C95_erase_everything_about_a_company(campaign_db: Engine) -> None:
    [first] = add(campaign_db, _place(1))
    add(campaign_db, _place(1), _place(2))  # même fiche dans une autre campagne
    with campaign_db.begin() as conn:
        add_alert(conn, "relance:1", "relance", "Rappeler · Commerce 1", f"/prospects/{first}", NOW)
        conn.exec_driver_sql(
            "INSERT INTO campaign_events (campaign_id, at, level, message) "
            "VALUES (1, now(), 'info', 'Commerce 1 : Site ajouté')"
        )
    assert erase_company(campaign_db, first) == 2
    assert _ids(campaign_db) == {"p2"}
    with campaign_db.connect() as conn:
        assert unseen_alerts(conn) == []
        left = "SELECT count(*) FROM campaign_events WHERE message LIKE 'Commerce 1%%'"
        assert conn.exec_driver_sql(left).scalar_one() == 0
        exclusions = load_exclusions(conn)
    assert len(exclusions.erased) == 1 and "p1" not in next(iter(exclusions.erased))
    assert erase_company(campaign_db, 999) == 0


def test_C95_blacklist_entry_erased_unless_kept_and_other_journals_untouched(
    campaign_db: Engine,
) -> None:
    from prospection.storage.exclusions import personal_lists, save_blacklist

    first = add(campaign_db, _place(1))[0]
    add(campaign_db, dataclasses.replace(_place(3), name="Commerce 1"))  # homonyme ailleurs
    with campaign_db.begin() as conn:
        save_blacklist(conn, ["Commerce 1", "Autre"])
        conn.exec_driver_sql(
            "INSERT INTO campaign_events (campaign_id, at, level, message) "
            "VALUES (2, now(), 'info', 'Commerce 1 : Site ajouté')"
        )
    erase_company(campaign_db, first)
    with campaign_db.connect() as conn:
        assert personal_lists(conn)[1] == ["Autre"]
        kept = ("SELECT count(*) FROM campaign_events "
                "WHERE campaign_id = 2 AND message LIKE 'Commerce%%'")  # fmt: skip
        assert conn.exec_driver_sql(kept).scalar_one() == 1  # l'homonyme garde son journal
    add(campaign_db, _place(4))
    with campaign_db.connect() as conn:
        other = conn.exec_driver_sql("SELECT id FROM prospects WHERE place_id = 'p4'").scalar_one()
    with campaign_db.begin() as conn:
        save_blacklist(conn, ["Commerce 4"])
    erase_company(campaign_db, other, keep_blacklist=True)
    with campaign_db.connect() as conn:
        assert personal_lists(conn)[1] == ["Commerce 4"]


def test_C94_exported_and_excluded_with_open_action_are_kept(campaign_db: Engine) -> None:
    [exported] = add(campaign_db, _place(1))
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET status = 'exporté'")
        insert_prospect(conn, 1, _place(2), "x", Verdict(False, ("Avec site",), ()), NOW)
        excluded = conn.exec_driver_sql(
            "SELECT id FROM prospects WHERE place_id = 'p2'"
        ).scalar_one()
        conn.exec_driver_sql(
            "INSERT INTO prospect_actions (prospect_id, kind, due_date, created_at) "
            "VALUES (%(id)s, 'rappeler', '2027-01-01', %(at)s)",
            {"id": excluded, "at": NOW},
        )
    assert purge(campaign_db, LATER) == 0 and exported
