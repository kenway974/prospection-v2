"""C133 : la liste d'un onglet est rangée par campagne, la plus récente d'abord."""

import dataclasses
from datetime import timedelta

from sqlalchemy import Engine

from prospection.application.prospect_listing import prospect_list, start_session
from prospection.domain.criteria import Verdict
from prospection.domain.prospect_source import CALLS, Scope
from prospection.storage.campaigns import create_campaign
from prospection.storage.prospect_list import load_session
from prospection.storage.prospects import insert_prospect
from tests.storage.test_campaigns import NOW, PLACE, REQUEST, STEPS


def _campaign(engine: Engine, name: str, *places: str, minutes: int) -> None:
    at = NOW + timedelta(minutes=minutes)
    with engine.begin() as conn:
        campaign_id = create_campaign(conn, dataclasses.replace(REQUEST, name=name), STEPS, at)
        for n, place in enumerate(places):
            row = dataclasses.replace(PLACE, place_id=place, name=place)
            insert_prospect(conn, campaign_id, row, "cuisiniste", Verdict(True, (), ()),
                            at + timedelta(seconds=n))  # fmt: skip


def test_C133_rows_grouped_by_campaign_newest_first(campaign_db: Engine) -> None:
    _campaign(campaign_db, "Lyon", "Martin", "Durand", minutes=0)
    _campaign(campaign_db, "Paris", "Bernard", minutes=10)
    listing = prospect_list(campaign_db, None, "", "nom", NOW, scope=Scope(CALLS))
    assert [(name, [r.data["name"] for r in rows]) for name, rows in listing.groups] == [
        ("Paris", ["Bernard"]), ("Lyon", ["Durand", "Martin"]),
    ]  # fmt: skip
    first = start_session(campaign_db, None, "", "nom", NOW, scope=Scope(CALLS))
    with campaign_db.connect() as conn:
        session = load_session(conn)
    assert session is not None and session.queue == [r.id for _, g in listing.groups for r in g]
    assert first == session.queue[0]
