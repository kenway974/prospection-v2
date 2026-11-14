"""C188 : sans email sur l'accueil, la page Contact (même si l'accueil a un formulaire) et
la page « Mentions légales » sont lues pour y trouver une adresse."""

import dataclasses

from tests.application.test_site_check import AZ, check
from tests.application.test_site_check_contact_page import pages

PLACE = dataclasses.replace(AZ, website="https://azenergie.fr/")
HOME_WITH_FORM = """<html><body><h1>AZ Énergie, électricien à Reims</h1>
<form><input type="email" name="email"><textarea name="message"></textarea></form>
<a href="/contact">Contact</a> <a href="/mentions-legales">Mentions légales</a></body></html>"""
CONTACT = "<html><body><p>Écrivez-nous : devis@azenergie.fr</p></body></html>"
LEGAL = "<html><body><p>Éditeur : AZ Énergie, gerant [at] azenergie [dot] fr</p></body></html>"


def test_C188_contact_page_read_for_an_email_even_with_a_form_on_home() -> None:
    report = check(pages({"/": HOME_WITH_FORM, "/contact": CONTACT}), PLACE)
    assert report.contacts is not None and "devis@azenergie.fr" in report.contacts.emails


def test_C188_legal_notice_page_read_for_an_email() -> None:
    report = check(pages({"/": HOME_WITH_FORM, "/mentions-legales": LEGAL}), PLACE)
    assert report.contacts is not None and "gerant@azenergie.fr" in report.contacts.emails


def test_C188_nothing_more_read_when_home_already_shows_an_email() -> None:
    from tests.fake_http import fake_client
    from tests.sources.test_web_reader import raw

    home = HOME_WITH_FORM.replace("<h1>", "<p>contact@azenergie.fr</p><h1>")
    client, recorder = fake_client(lambda r: raw(home.encode()))
    check(client, PLACE)
    assert len(recorder.requests) == 1


def test_C188_host_and_web_agency_addresses_are_not_kept() -> None:
    legal = """<html><body><p>Hébergeur : o2switch, support@o2switch.fr</p>
    <p>Réalisation : Agence Pixel, contact@agencepixel.fr</p>
    <p>Éditeur : gerant.az@orange.fr</p></body></html>"""
    report = check(pages({"/": HOME_WITH_FORM, "/mentions-legales": legal}), PLACE)
    assert report.contacts is not None and report.contacts.emails == ("gerant.az@orange.fr",)


def test_C188_page_moved_to_another_site_is_ignored() -> None:
    import httpx

    from tests.fake_http import fake_client
    from tests.sources.test_web_reader import raw

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.host == "agence.fr":
            return raw(b"<p>contact@azenergie.fr</p>")
        if request.url.path == "/mentions-legales":
            return httpx.Response(301, headers={"Location": "https://agence.fr/legal"})
        return raw(HOME_WITH_FORM.encode())

    report = check(fake_client(answer)[0], PLACE)
    assert report.contacts is not None and report.contacts.emails == ()


def _home(links: str) -> str:
    return HOME_WITH_FORM.replace('<a href="/mentions-legales">Mentions légales</a>', links)


def test_C188_pdf_legal_notice_skipped_for_the_html_one() -> None:
    pdf = "/mentions-legales.pdf"
    links = f'<a href="{pdf}">Mentions légales</a> <a href="/mentions-legales">Mentions</a>'
    site = {"/": _home(links), pdf: "<p>rien</p>", "/mentions-legales": LEGAL}
    report = check(pages(site), PLACE)
    assert report.contacts is not None and "gerant@azenergie.fr" in report.contacts.emails


def test_C188_same_site_with_or_without_www() -> None:
    links = '<a href="https://www.azenergie.fr/mentions-legales">Mentions légales</a>'
    report = check(pages({"/": _home(links), "/mentions-legales": LEGAL}), PLACE)
    assert report.contacts is not None and "gerant@azenergie.fr" in report.contacts.emails
