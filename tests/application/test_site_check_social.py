"""C154 : une fiche Google qui renvoie vers un réseau social ou un annuaire est « sans site »."""

import dataclasses

from prospection.application.site_verdict import WITH_SITE_REASON, with_site
from prospection.domain.criteria import Criteria, Verdict
from tests.application.campaign_helpers import request
from tests.application.test_site_check import AZ, SITE, check, site
from tests.fake_http import fake_client
from tests.sources.test_web_reader import raw


def test_C154_instagram_is_not_read_as_a_site() -> None:
    place = dataclasses.replace(AZ, website="https://www.instagram.com/ortopaysage?igsh=eXpm")
    client, recorder = fake_client(lambda r: raw(b"<html>instagram</html>"))
    report = check(client, place)
    assert report.url is None and report.audit is None and report.parked
    assert report.problem == "La fiche Google renvoie vers Instagram : pas de vrai site"
    assert all(r.url.host != "www.instagram.com" for r in recorder.requests)


def test_C154_social_link_counts_as_no_site_in_the_criteria() -> None:
    place = dataclasses.replace(AZ, website="https://linktr.ee/ortopaysage")
    report = check(site({}), place)
    verdict = with_site(Verdict(False, (WITH_SITE_REASON,), ()), report, _criteria())
    assert verdict.qualified


def test_C154_real_site_still_found_from_the_name() -> None:
    place = dataclasses.replace(AZ, website="https://facebook.com/azenergie")
    report = check(site({"azenergie.fr": SITE}), place)
    assert report.origin == "retrouvé" and report.url == "https://azenergie.fr"


def _criteria() -> Criteria:
    return request().criteria
