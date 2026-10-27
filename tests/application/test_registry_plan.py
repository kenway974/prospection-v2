"""C24, C25 : étapes « registre » d'une campagne."""

from datetime import UTC, datetime

from prospection.application.campaigns import build_steps
from prospection.domain.campaign_request import CampaignRequest, CityZone, RadiusZone
from prospection.domain.criteria import Criteria

LYON = CityZone("Lyon", "69123", 45.76, 4.83)


def request(*zones: CityZone | RadiusZone, days: int = 90) -> CampaignRequest:
    criteria = Criteria(created_within_days=days)
    return CampaignRequest("Test", ("cuisiniste",), zones, 10, criteria, False, ("registre",))


def test_C24_window_counts_days_from_today_in_paris() -> None:
    late_evening = datetime(2026, 10, 26, 23, 30, tzinfo=UTC)  # déjà le 27 à Paris
    [step] = build_steps(request(LYON, days=90), late_evening)
    assert step.registry is not None
    assert step.registry["until"] == "2026-10-27"
    assert step.registry["since"] == "2026-07-30"  # 90 jours, aujourd'hui compris


def test_C25_radius_searches_the_whole_department_and_says_so() -> None:
    [step] = build_steps(request(RadiusZone(LYON, 10)), datetime(2026, 10, 26, tzinfo=UTC))
    assert step.registry is not None
    assert (step.registry["area"], step.registry["code"]) == ("departement", "69")
    assert "département" in step.query
