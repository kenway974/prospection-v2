"""C13 : seuls les établissements de la zone choisie sont gardés."""

from sqlalchemy import Engine

from prospection.application.campaigns import create_campaign, progress
from prospection.domain.campaign_request import CampaignRequest, DepartmentZone, RadiusZone
from prospection.domain.criteria import Criteria
from tests.application.campaign_helpers import LYON, NOW, api_place, pages
from tests.application.test_campaign_step import run_all
from tests.fake_http import fake_client


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
