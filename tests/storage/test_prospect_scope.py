"""C127, C128 : prospects Terrain à part, liste filtrée par campagne."""

import dataclasses
from datetime import timedelta

from sqlalchemy import Connection

from prospection.domain.criteria import Verdict
from prospection.domain.prospect_source import CALLS, FIELD, Scope
from prospection.storage.campaigns import create_campaign
from prospection.storage.prospect_list import source_counts, status_counts
from prospection.storage.prospect_scope import campaign_choices
from prospection.storage.prospects import insert_prospect
from tests.storage.test_call_tracking import prospect_ids
from tests.storage.test_campaigns import NOW, PLACE, REQUEST, STEPS


def _campaign(conn: Connection, name: str, places: int, kind: str = CALLS) -> list[int]:
    campaign_id = create_campaign(
        conn, dataclasses.replace(REQUEST, name=name), STEPS, NOW, kind=kind
    )
    for n in range(places):
        place = dataclasses.replace(PLACE, place_id=f"{name}{n}", name=f"{name} {n}")
        insert_prospect(conn, campaign_id, place, "cuisiniste", Verdict(True, (), ()),
                        NOW + timedelta(minutes=n))  # fmt: skip
    return [campaign_id]


def test_C127_field_prospects_apart_from_calls(conn: Connection) -> None:
    _campaign(conn, "Appels", 2)
    _campaign(conn, "Terrain", 1, FIELD)
    calls, field = (
        prospect_ids(conn, None, "", "trouves", Scope(CALLS)),
        prospect_ids(conn, None, "", "trouves", Scope(FIELD)),
    )
    assert len(calls) == 2 and len(field) == 1 and not set(calls) & set(field)
    assert len(prospect_ids(conn, None, "", "trouves")) == 3  # export : toutes les origines
    assert status_counts(conn, "", Scope(FIELD)) == {"à appeler": 1}
    assert source_counts(conn, "") == {CALLS: 2, FIELD: 1}
    assert source_counts(conn, "terrain 0") == {FIELD: 1}


def test_C128_list_filtered_by_campaign(conn: Connection) -> None:
    [first] = _campaign(conn, "Lyon", 2)
    [second] = _campaign(conn, "Paris", 1)
    _campaign(conn, "Terrain", 1, FIELD)
    assert campaign_choices(conn, CALLS) == [(second, "Paris", 1), (first, "Lyon", 2)]
    only_lyon = prospect_ids(conn, None, "", "trouves", Scope(CALLS, first))
    assert len(only_lyon) == 2
    assert prospect_ids(conn, None, "", "trouves", Scope(FIELD, first)) == []
