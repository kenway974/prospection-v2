"""Site de la fiche Google : nouvel essai en http, page d'hébergeur, version du serveur."""

import dataclasses
from datetime import date

import httpx

from prospection.application.site_check import PLACEHOLDER, check_site
from prospection.domain.opportunity import opportunity
from prospection.domain.signals import signals_of
from tests.application.test_site_check import AZ, SITE
from tests.fake_http import fake_client

OVH = """<html><head><title>Site en construction</title></head>
<body><h1>Site en construction</h1></body></html>"""


def server(pages: dict[str, tuple[str, dict[str, str]]]) -> httpx.Client:
    """Clé : « schéma://hôte » ; https refusé (certificat cassé) si absent."""

    def handler(request: httpx.Request) -> httpx.Response:
        found = pages.get(f"{request.url.scheme}://{request.url.host}")
        if found is None:
            raise httpx.ConnectError("certificat invalide", request=request)
        body, headers = found
        return httpx.Response(200, headers={"Content-Type": "text/html", **headers},
                              stream=httpx.ByteStream(body.encode()))  # fmt: skip

    return fake_client(handler)[0]


def test_google_site_retried_in_http_when_https_is_broken() -> None:
    place = dataclasses.replace(AZ, website="https://azenergie.fr/")
    report = check_site(server({"http://azenergie.fr": (SITE, {})}), place, ("electricien",), 2026)
    assert report.url == "http://azenergie.fr/" and report.audit is not None
    assert "Pas de HTTPS" in report.audit.problems


def test_hosting_placeholder_counts_as_no_site() -> None:
    place = dataclasses.replace(AZ, website="https://yamtch.com/")
    report = check_site(server({"https://yamtch.com": (OVH, {})}), place, ("restaurant",), 2026)
    assert report.parked and report.problem == PLACEHOLDER and report.audit is None
    s = signals_of(place, report, None, None, (), date(2026, 10, 29))
    assert not s.has_site and not s.site_down
    assert ("Aucun site (ni sur la fiche Google, ni retrouvé)", 55) in opportunity(s)[1]


def test_old_php_reported_from_the_server_header() -> None:
    place = dataclasses.replace(AZ, website="http://chef.fr/")
    pages = {"http://chef.fr": (SITE, {"X-Powered-By": "PHP/5.6.40"})}
    report = check_site(server(pages), place, ("traiteur",), 2026)
    assert report.audit is not None
    assert "Serveur PHP ancien (5.6), sans correctifs de sécurité" in report.audit.problems
