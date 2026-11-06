"""C153 : formulaire basique (nom, email, message) ou formulaire de devis détaillé (champs du
métier : type de travaux, surface, photos, date…)."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit
from prospection.domain.site_card import site_lines
from prospection.domain.site_form import BASIC, DETAILED, form_detail
from prospection.domain.site_report import SiteReport

TEXT = "<h1>Paysagiste</h1><p>" + "jardin " * 250 + "</p>"
BASIC_FORM = """<form><input name="nom"><input type="email" name="email">
<input type="checkbox" name="rgpd"><textarea name="message"></textarea></form>"""
QUOTE_FORM = """<form><input name="nom"><input type="email" name="email">
<select name="prestation"><option>Taille de haies</option></select>
<input name="surface" placeholder="Surface du jardin (m²)"><input type="file" name="photos">
<textarea name="message"></textarea></form>"""


def test_C153_basic_form_said_and_counted_as_small_problem() -> None:
    page = parse_page(TEXT + BASIC_FORM)
    assert form_detail(page, ()) == BASIC
    report = audit(page, "https://p.fr", 1, 2026)
    assert report.form_detail == BASIC and "form_basic" in report.codes


def test_C153_quote_form_with_trade_fields_is_detailed() -> None:
    page = parse_page(TEXT + QUOTE_FORM)
    assert form_detail(page, ()) == DETAILED
    assert "form_basic" not in audit(page, "https://p.fr", 1, 2026).codes


def test_C153_detail_read_on_the_contact_page_too() -> None:
    home, contact = parse_page(TEXT), parse_page(QUOTE_FORM)
    assert form_detail(home, (contact,)) == DETAILED


def test_C153_no_visible_fields_no_verdict() -> None:
    widget = parse_page(TEXT + '<div class="nf-form-cont"></div>')
    assert form_detail(widget, ()) is None


def test_C153_card_shows_place_and_detail() -> None:
    report = audit(parse_page(TEXT + BASIC_FORM), "https://p.fr", 1, 2026)
    lines = dict(site_lines(SiteReport("fiche Google", "https://p.fr", audit=report)))
    assert lines["Formulaire"] == "plus bas sur l'accueil · basique (nom, email, message)"
