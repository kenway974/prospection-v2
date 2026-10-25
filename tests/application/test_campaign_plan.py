"""C15, C16 : une requête n'est lue qu'une fois par zone ; l'estimation compte ce qui sera lu."""

from sqlalchemy import Engine

from prospection.application.campaigns import build_steps
from prospection.application.search_screen import estimate_raw
from prospection.domain.campaign_request import CampaignRequest, DepartmentZone, RawRequest
from prospection.domain.criteria import Criteria
from tests.application.campaign_helpers import LYON, NOW, PRICING

RHONE = DepartmentZone("69", "Rhône")


def test_C15_same_query_and_zone_read_once() -> None:
    request = CampaignRequest(
        "Test", ("cuisiniste", "Cuisine sur mesure", "cuisiniste"), (LYON, LYON, RHONE), 9,
        Criteria(), True,
    )  # fmt: skip
    queries = [(s.query, s.zone_label) for s in build_steps(request)]
    assert len(queries) == len(set(queries)) == 6
    assert sorted(q for q, _ in queries) == sorted(
        [f"{q} {z}" for q in ("cuisiniste", "magasin de cuisines équipées", "cuisine sur mesure")
         for z in ("Lyon", "Rhône")]
    )  # fmt: skip


def test_C16_estimate_counts_the_pages_the_campaign_may_read(campaign_db: Engine) -> None:
    raw = RawRequest(
        "Test", ["cuisiniste", "cuisine sur mesure"], [LYON, LYON, RHONE], 9, Criteria(), True
    )
    estimate = estimate_raw(campaign_db, PRICING, raw, NOW)
    assert estimate.pages == 6 * 3
