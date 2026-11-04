"""C138 : sans formulaire sur l'accueil, la page Contact du site est lue (formulaire, emails)."""

import dataclasses

import httpx

from prospection.domain.site_form import CONTACT_PAGE, HOME_TOP
from tests.application.test_site_check import AZ, check
from tests.fake_http import fake_client
from tests.sources.test_web_reader import raw

PLACE = dataclasses.replace(AZ, website="https://azenergie.fr/")
HOME = """<html><head><title>AZ Énergie, électricien à Reims</title></head><body>
<h1>Électricien Reims</h1><a href="/nous-contacter">Contact</a></body></html>"""
CONTACT = """<html><body><form><input name="your-email"><textarea></textarea></form>
<p>Écrivez-nous : devis@azenergie.fr</p></body></html>"""


def pages(by_path: dict[str, str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        body = by_path.get(request.url.path)
        return raw(body.encode()) if body else raw(b"", 404)

    return fake_client(handler)[0]


def test_C138_contact_page_read_when_home_has_no_form() -> None:
    report = check(pages({"/": HOME, "/nous-contacter": CONTACT}), PLACE)
    assert report.audit is not None and report.audit.form_place == CONTACT_PAGE
    assert "Pas de formulaire de contact" not in report.audit.problems
    assert report.contacts is not None and "devis@azenergie.fr" in report.contacts.emails


def test_C138_no_extra_reading_when_home_has_a_form() -> None:
    home = HOME.replace("<h1>", '<form><input type="tel"></form><h1>')
    client, recorder = fake_client(lambda r: raw(home.encode()))
    report = check(client, PLACE)
    assert report.audit is not None and report.audit.form_place == HOME_TOP
    assert len(recorder.requests) == 1
