"""C121 : une zone porte son pays ; Google reçoit la région de ce pays."""

import json

from sqlalchemy import Engine

from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign
from prospection.domain.campaign_request import CampaignRequest, CityZone, DepartmentZone
from prospection.domain.criteria import Criteria
from prospection.storage.campaign_codec import decode_request
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages
from tests.fake_http import fake_client

LIEGE = CityZone("Liège", "WAL", 50.6326, 5.5797, "BE")


def test_C121_zone_labels_name_the_country() -> None:
    assert LIEGE.label == "Liège (BE-WAL)"
    assert DepartmentZone("VD", "Canton de Vaud", "CH").label == "Canton de Vaud (CH)"
    assert CityZone("Lyon", "69123", 45.76, 4.83).label == "Lyon (69)"


def test_C121_google_searches_with_the_zone_country(campaign_db: Engine) -> None:
    client, recorder = fake_client(pages([api_place(1)]))
    belgian = CampaignRequest("Liège", ("cuisiniste",), (LIEGE,), 1, Criteria(phone="any"), False)
    campaign_id = create_campaign(campaign_db, belgian, NOW)
    run_step(campaign_db, BOX, client, PRICING, campaign_id, NOW)
    body = json.loads(recorder.requests[0].content)
    assert (body["textQuery"], body["regionCode"]) == ("cuisiniste Liège", "BE")


def test_C121_campaigns_saved_before_countries_stay_in_france() -> None:
    old = {
        "name": "x", "trades": ["cuisiniste"], "target": 5, "synonyms_on": False,
        "criteria": {"min_reviews": None, "max_reviews": 30, "website": "any",
                     "phone": "with", "exclude_franchises": True},
        "zones": [{"kind": "department", "code": "69", "name": "Rhône"}],
    }  # fmt: skip
    assert decode_request(old).zones == (DepartmentZone("69", "Rhône", "FR"),)
