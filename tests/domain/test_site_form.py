"""C137, C139 : formulaire de contact reconnu (champs, services, page coupée) et son emplacement."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_form import (
    CONTACT_PAGE,
    HOME,
    HOME_TOP,
    NONE,
    UNKNOWN,
    contact_links,
    form_place,
    has_form,
)

TEXT = "<p>" + "plomberie " * 200 + "</p>"


def test_C137_email_field_typed_as_text_is_a_contact_form() -> None:
    divi = '<form><input type="text" name="et_pb_contact_email_0"><textarea></textarea></form>'
    assert has_form(parse_page(divi))
    named = '<form><input name="your-name"><input type="text" placeholder="Votre e-mail"></form>'
    assert has_form(parse_page(named))


def test_C137_phone_or_message_field_named_without_type() -> None:
    page = parse_page('<form><input name="telephone"><input name="nom"></form>')
    assert has_form(page)


def test_C137_newsletter_or_search_alone_is_not_enough() -> None:
    assert not has_form(parse_page('<form role="search"><input type="email"></form>'))
    assert not has_form(parse_page('<form><input type="password"><input name="email"></form>'))


def test_C137_form_from_a_form_service_is_recognised() -> None:
    for src in (
        "https://docs.google.com/forms/d/e/1FAI/viewform?embedded=true",
        "https://form.typeform.com/to/abc",
        "https://js.hsforms.net/forms/v2.js",
        "https://tally.so/embed/w4", "https://form.jotform.com/2412",
        "https://sibforms.com/serve/MUIF",
    ):  # fmt: skip
        assert has_form(parse_page(f'<iframe src="{src}"></iframe>')), src


def test_C137_form_left_open_at_the_end_of_a_cut_page_still_counts() -> None:
    page = parse_page(TEXT + '<form><input type="email" name="email"><textarea>', truncated=True)
    assert has_form(page)


def test_C139_place_on_home_top_or_lower() -> None:
    top = parse_page('<h1>Plombier</h1><form><input type="tel"></form>' + TEXT)
    low = parse_page(TEXT + '<form><input type="tel"></form>')
    assert form_place(top, (), None) == HOME_TOP
    assert form_place(low, (), None) == HOME


def test_C139_place_on_contact_page_or_none() -> None:
    home = parse_page(TEXT)
    contact = parse_page('<form><input type="email"></form>')
    assert form_place(home, (contact,), None) == CONTACT_PAGE
    assert form_place(home, (parse_page(TEXT),), None) == NONE


def test_C138_cut_page_or_javascript_builder_is_never_said_formless() -> None:
    cut = parse_page(TEXT, truncated=True)
    assert form_place(cut, (), None) == UNKNOWN
    assert form_place(parse_page(TEXT), (), "Wix") == UNKNOWN


def test_C138_contact_links_same_site_best_first_two_at_most() -> None:
    page = parse_page(
        '<a href="/a-propos">Qui</a><a href="https://autre.fr/contact">x</a>'
        '<a href="/nous-contacter/">Contact</a><a href="mailto:a@b.fr">m</a>'
        '<a href="https://www.plombier.fr/devis-gratuit">Devis</a>'
        '<a href="/prendre-rendez-vous">RDV</a><a href="#contact">ancre</a>'
    )
    links = contact_links(page, "https://www.plombier.fr/")
    assert links == [
        "https://www.plombier.fr/nous-contacter/", "https://www.plombier.fr/devis-gratuit",
    ]  # fmt: skip


def test_C138_contact_link_found_by_its_text() -> None:
    page = parse_page('<a href="/page-12">Nous écrire</a><a href="/p-3">Accueil</a>')
    assert contact_links(page, "https://plombier.fr") == ["https://plombier.fr/page-12"]
