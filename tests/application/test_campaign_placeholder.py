"""C131 : une page « en construction » compte comme « sans site »."""

from sqlalchemy import Engine

from prospection.application.campaigns import progress
from prospection.application.prospect_listing import prospect_list
from prospection.domain.criteria import Criteria
from prospection.domain.site_report import SiteReport
from tests.application.campaign_helpers import api_place
from tests.application.test_campaign_sites import GOOD, FakeSites, run


def test_C131_placeholder_page_kept_when_no_site_wanted(campaign_db: Engine) -> None:
    parked = SiteReport("fiche Google", problem="Page en construction", parked=True)
    real = SiteReport("fiche Google", "https://martin.fr", audit=GOOD)
    sites = FakeSites({"Cuisines Martin 1": parked, "Cuisines Martin 2": real})
    places = [{**api_place(n), "websiteUri": f"https://martin{n}.fr"} for n in (1, 2)]
    campaign_id = run(campaign_db, Criteria(phone="any", website="without"), places, sites)
    assert sorted(sites.checked) == ["Cuisines Martin 1", "Cuisines Martin 2"]
    assert progress(campaign_db, campaign_id).qualified == 1
    [row] = prospect_list(campaign_db, None, "", "trouves").rows
    assert row.data["name"] == "Cuisines Martin 1"
