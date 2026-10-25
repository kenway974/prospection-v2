"""C34 à C41, C79 : une campagne avance page par page et s'arrête au bon moment."""

import httpx
from sqlalchemy import Engine

from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign, progress, request_stop
from prospection.domain.campaign_request import CampaignRequest, DepartmentZone, RadiusZone
from prospection.domain.criteria import Criteria
from prospection.storage.google_usage import month_usage
from tests.application.campaign_helpers import (
    BOX,
    LYON,
    NOW,
    PRICING,
    api_place,
    pages,
    request,
)
from tests.fake_http import fake_client


def run_all(engine: Engine, campaign_id: int, client: httpx.Client, limit: int = 20) -> None:
    for _ in range(limit):
        if run_step(engine, BOX, client, PRICING, campaign_id, NOW).done:
            return
    raise AssertionError("la campagne ne s'arrête pas")


def usage(engine: Engine) -> tuple[int, int]:
    with engine.connect() as conn:
        return month_usage(conn, "2026-10")


def test_C36_continues_until_target(campaign_db: Engine) -> None:
    client, recorder = fake_client(
        pages([api_place(1), api_place(2)], [api_place(3), api_place(4)])
    )
    campaign_id = create_campaign(campaign_db, request(target=3), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.status, state.qualified, state.found) == ("done", 4, 4)
    assert state.stop_reason == "Objectif atteint : 4 prospects qualifiés."
    assert len(recorder.requests) == 2


def test_C37_stops_when_source_exhausted_with_reason(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1, reviews=99), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert state.stop_reason == (
        "Plus de résultats sur Google Maps pour ces métiers et cette zone "
        "(1 qualifié sur 5 voulus)."
    )
    assert state.exclusion_counts == [("Trop d'avis", 1)]


def test_C37_C07_stops_at_free_quota_with_reason_and_keeps_prospects(campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO google_usage (month, calls, cost_cents) VALUES ('2026-10', 999, 0)"
        )
    client, recorder = fake_client(pages([api_place(1)], [api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert state.stop_reason == (
        "Quota gratuit de Google atteint pour ce mois : 1 qualifié sur 5 voulus, gardés. "
        "Pour continuer, relevez le plafond dans Réglages → Budget Google, "
        "ou attendez le 1er du mois."
    )
    assert (state.qualified, len(recorder.requests), usage(campaign_db)) == (1, 1, (1000, 0))


def test_C35_stop_keeps_found(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1)], [api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=5), NOW)
    run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW)
    request_stop(campaign_db, campaign_id, NOW)
    assert run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW).done
    state = progress(campaign_db, campaign_id)
    assert (state.status, state.qualified, state.stop_reason) == (
        "done",
        1,
        "Arrêtée à votre demande : les prospects trouvés sont gardés.",
    )


def test_C38_duplicate_across_keywords_counted_once(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1)], [api_place(1), api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    run_all(campaign_db, campaign_id, client)
    assert progress(campaign_db, campaign_id).found == 2


def test_C41_bad_place_does_not_stop(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([{"id": "sans-nom"}, api_place(2)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert state.qualified == 1
    assert any("1 établissement illisible ignoré" in e.message for e in state.recent_events)


def test_C79_cost_recorded_per_campaign(campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO google_usage (month, calls, cost_cents) VALUES ('2026-10', 1000, 0)"
        )
        conn.exec_driver_sql("UPDATE app_settings SET google_budget_cents = 500")
    client, _ = fake_client(pages([api_place(1)]))
    campaign_id = create_campaign(campaign_db, request(target=9), NOW)
    run_all(campaign_db, campaign_id, client)
    assert progress(campaign_db, campaign_id).cost_cents == 4
    assert usage(campaign_db) == (1001, 4)


def test_C13_place_outside_radius_excluded(campaign_db: Engine) -> None:
    far = {**api_place(2), "location": {"latitude": 46.5, "longitude": 4.83}}
    client, _ = fake_client(pages([api_place(1), far]))
    radius_request = CampaignRequest(
        "Test", ("cuisiniste",), (RadiusZone(LYON, 15),), 9, Criteria(phone="any"), False
    )
    campaign_id = create_campaign(campaign_db, radius_request, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.qualified, state.exclusion_counts) == (1, [("Hors zone", 1)])


def test_C07_free_quota_used_up_stays_used_up_until_google_resets_it(campaign_db: Engine) -> None:
    from datetime import UTC, datetime

    with campaign_db.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO google_usage (month, calls, cost_cents) VALUES ('2026-10', 1000, 0)"
        )
    paris_morning = datetime(2026, 11, 1, 5, 0, tzinfo=UTC)  # 6h à Paris, octobre chez Google
    client, recorder = fake_client(pages([api_place(1)]))
    campaign_id = create_campaign(campaign_db, request(), paris_morning)
    assert run_step(campaign_db, BOX, client, PRICING, campaign_id, paris_morning).done
    assert recorder.requests == []


def test_C13_place_outside_department_excluded(campaign_db: Engine) -> None:
    paris = {**api_place(2), "formattedAddress": "3 rue de Rivoli, 75001 Paris, France"}
    lyon = {**api_place(1), "formattedAddress": "3 rue de la Ré, 69002 Lyon, France"}
    client, _ = fake_client(pages([lyon, paris]))
    rhone = CampaignRequest(
        "Test", ("cuisiniste",), (DepartmentZone("69", "Rhône"),), 9, Criteria(phone="any"), False
    )
    campaign_id = create_campaign(campaign_db, rhone, NOW)
    run_all(campaign_db, campaign_id, client)
    state = progress(campaign_db, campaign_id)
    assert (state.qualified, state.exclusion_counts) == (1, [("Hors zone", 1)])
