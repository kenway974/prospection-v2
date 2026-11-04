"""C138, C139 : l'audit tient compte des pages Contact lues et dit où est le formulaire."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit
from prospection.domain.site_form import CONTACT_PAGE, HOME_TOP, UNKNOWN

HOME = "<html><body><h1>Plombier</h1><p>" + "fuite " * 250 + "</p></body></html>"
CONTACT = '<html><body><form><input type="email"><textarea></textarea></form></body></html>'
NO_FORM = "Pas de formulaire de contact"
ONLY_CONTACT = "Formulaire seulement sur une page Contact : invisible depuis l'accueil"


def test_C138_form_on_contact_page_is_found() -> None:
    report = audit(parse_page(HOME), "https://p.fr", 1, 2026, others=(parse_page(CONTACT),))
    assert report.contact_form and report.form_place == CONTACT_PAGE
    assert NO_FORM not in report.problems and ONLY_CONTACT in report.problems


def test_C139_form_on_top_of_home_is_best() -> None:
    home = HOME.replace("<h1>Plombier</h1>", "<h1>Plombier</h1>" + CONTACT)
    report = audit(parse_page(home), "https://p.fr", 1, 2026)
    assert report.form_place == HOME_TOP and report.contact_form
    assert not {NO_FORM, ONLY_CONTACT} & set(report.problems)


def test_C138_unsure_is_not_a_problem() -> None:
    report = audit(parse_page(HOME, truncated=True), "https://p.fr", 1, 2026)
    assert report.form_place == UNKNOWN and NO_FORM not in report.problems
    assert report.contact_form  # aucun manque constaté : ni problème, ni douleur, ni filtre


def test_C139_no_form_anywhere_stays_critical() -> None:
    report = audit(parse_page(HOME), "https://p.fr", 1, 2026, others=(parse_page(HOME),))
    assert NO_FORM in report.problems
