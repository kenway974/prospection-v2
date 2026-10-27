"""C46 à C52 : rapport du site d'un établissement (lu, retrouvé, probable, absent)."""

import dataclasses

import httpx

from prospection.application.site_check import check_site
from prospection.domain.place import Place
from prospection.domain.site_report import SiteReport
from tests.fake_http import fake_client
from tests.sources.test_web_reader import raw
from tests.storage.test_campaigns import PLACE

AZ = dataclasses.replace(
    PLACE, name="AZ Énergie", address="12 rue de Vesle, 51100 Reims, France",
    phone="+33326123456", website=None, country="FR",
)  # fmt: skip
SITE = """<html><head><title>AZ Énergie, électricien à Reims</title></head><body>
<h1>Électricien Reims</h1><p>Appelez le 03 26 12 34 56</p>
<a href="mailto:contact@azenergie.fr">Écrire</a></body></html>"""


def site(pages: dict[str, str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(request.url.host)
        if body is None:
            raise httpx.ConnectError("inconnu", request=request)
        return raw(body.encode())

    return fake_client(handler)[0]


def check(client: httpx.Client, place: Place = AZ) -> SiteReport:
    return check_site(client, place, ("electricien",), 2026)


def test_C50_site_from_google_is_read_and_audited() -> None:
    place = dataclasses.replace(AZ, website="https://azenergie.fr/")
    report = check(site({"azenergie.fr": SITE}), place)
    assert report.origin == "fiche Google" and report.url == "https://azenergie.fr/"
    assert report.audit is not None and "Pas de HTTPS" not in report.audit.problems
    assert report.seo is not None and report.seo.city["titre"]
    assert report.contacts is not None and report.contacts.emails == ("contact@azenergie.fr",)


def test_C46_missing_site_found_and_adopted() -> None:
    report = check(site({"az-energie.fr": SITE}))
    assert report.origin == "retrouvé" and report.url == "https://az-energie.fr"
    assert report.audit is not None


def test_C47_homonym_not_adopted_only_reported() -> None:
    other = "<html><title>AZ Énergie Lille</title><p>AZ Énergie, 59000 Lille</p></html>"
    report = check(site({"azenergie.fr": other}))
    assert report.origin == "aucun" and report.url is None and report.audit is None
    assert report.probable == "https://azenergie.fr"


def test_no_site_anywhere() -> None:
    report = check(site({}))
    assert (report.origin, report.url, report.probable, report.problem) == (
        "aucun",
        None,
        None,
        None,
    )


def test_unreadable_site_said_plainly() -> None:
    place = dataclasses.replace(AZ, website="https://azenergie.fr/")
    report = check(site({}), place)
    assert report.origin == "fiche Google" and report.problem == "Site injoignable"
    assert report.audit is None
