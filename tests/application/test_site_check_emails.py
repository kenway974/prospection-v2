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
