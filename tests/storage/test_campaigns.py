"""Stockage des campagnes (C18, C38, C40, C07)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import Connection

from prospection.domain.campaign_request import CampaignRequest, CityZone, RadiusZone
from prospection.domain.criteria import Criteria, Verdict
from prospection.domain.place import Circle, Place
from prospection.storage.campaign_codec import decode_request, encode_request
from prospection.storage.campaign_steps import StepSpec, next_step, record_page
from prospection.storage.campaigns import add_event, create_campaign, load_campaign, recent_events
from prospection.storage.google_usage import add_call, lock_google, month_usage
from prospection.storage.prospects import exclusion_counts, insert_prospect, seen_place_ids
from prospection.storage.templates import list_templates, save_template

NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
LYON = CityZone("Lyon", "69123", 45.76, 4.83)
REQUEST = CampaignRequest(
    "Cuisinistes", ("cuisiniste",), (LYON, RadiusZone(LYON, 15)), 20, Criteria(), True
)
STEPS = [StepSpec("cuisiniste Lyon", "cuisiniste", "Lyon (69)", Circle(45.76, 4.83, 10_000))]
PLACE = Place(
    "p1", "Atelier", "Lyon", 45.7, 4.8, ("store",), None, "OPERATIONAL", "+33612345678", None,
    None, 0, (), None, 0, "inconnu",
)  # fmt: skip


def test_request_roundtrip() -> None:
    assert decode_request(encode_request(REQUEST)) == REQUEST


def test_C40_next_page_saved_with_results_atomically(conn: Connection) -> None:
    campaign_id = create_campaign(conn, REQUEST, STEPS, NOW)
    step = next_step(conn, campaign_id)
    assert step is not None and (step.page_number, step.page_token) == (0, None)
    record_page(conn, step.id, next_token="tok2")
    step = next_step(conn, campaign_id)
    assert step is not None and (step.page_number, step.page_token) == (1, "tok2")
    record_page(conn, step.id, next_token=None)
    assert next_step(conn, campaign_id) is None


def test_steps_end_after_three_pages(conn: Connection) -> None:
    campaign_id = create_campaign(conn, REQUEST, STEPS, NOW)
    for token in ["t1", "t2", "t3"]:
        step = next_step(conn, campaign_id)
        assert step is not None
        record_page(conn, step.id, next_token=token)
    assert next_step(conn, campaign_id) is None


def test_C38_unique_place_per_campaign(conn: Connection) -> None:
    campaign_id = create_campaign(conn, REQUEST, STEPS, NOW)
    verdict = Verdict(False, ("Trop d'avis (40)",), ())
    insert_prospect(conn, campaign_id, PLACE, "cuisiniste", verdict, NOW)
    insert_prospect(conn, campaign_id, PLACE, "cuisine sur mesure", verdict, NOW)
    assert seen_place_ids(conn, campaign_id) == {"p1"}
    assert exclusion_counts(conn, campaign_id) == [("Trop d'avis", 1)]
    campaign = load_campaign(conn, campaign_id)
    assert campaign.request == REQUEST and campaign.status == "queued"


def test_C07_usage_counter_is_atomic_under_lock(conn: Connection) -> None:
    lock_google(conn)
    assert month_usage(conn, "2026-10") == (0, 0)
    add_call(conn, "2026-10", cost_cents=0)
    add_call(conn, "2026-10", cost_cents=4)
    assert month_usage(conn, "2026-10") == (2, 4)
    assert month_usage(conn, "2026-11") == (0, 0)


def test_events_kept_newest_first(conn: Connection) -> None:
    campaign_id = create_campaign(conn, REQUEST, STEPS, NOW)
    add_event(conn, campaign_id, NOW, "info", "Page 1 lue")
    add_event(conn, campaign_id, NOW.replace(minute=1), "warning", "Google trop sollicité")
    assert [e.message for e in recent_events(conn, campaign_id, 5)] == [
        "Google trop sollicité",
        "Page 1 lue",
    ]


def test_C18_template_saved_and_listed(conn: Connection) -> None:
    save_template(conn, "Cuisinistes Lyon", REQUEST)
    save_template(conn, "Cuisinistes Lyon", REQUEST)
    assert [(t.name, t.request) for t in list_templates(conn)] == [("Cuisinistes Lyon", REQUEST)]


@pytest.mark.parametrize("blank", ["", "  "])
def test_template_needs_a_name(conn: Connection, blank: str) -> None:
    with pytest.raises(ValueError):
        save_template(conn, blank, REQUEST)
