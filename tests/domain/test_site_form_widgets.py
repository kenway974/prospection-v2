"""C137 : formulaires dessinés en JavaScript reconnus à la trace laissée dans le HTML
(widget de constructeur ou d'extension), sans lancer de navigateur."""

import pytest

from prospection.domain.html_page import parse_page
from prospection.domain.site_form import HOME, HOME_TOP, NONE, form_place, has_form

TEXT = "<p>" + "plomberie " * 200 + "</p>"


@pytest.mark.parametrize(
    "widget",
    [
        '<div class="nf-form-cont"></div>',  # Ninja Forms (WordPress) : conteneur vide + JS
        '<div class="sqs-block form-block sqs-block-form"></div>',  # Squarespace
        '<div class="wsite-form-container"><div class="wsite-form"></div></div>',  # Weebly
        '<div class="j-module j-formnew"></div>',  # Jimdo
        '<div class="w-form"></div>',  # Webflow
        '<section class="wixui-form"></section>',  # Wix
        '<script>{"appDefinitionId":"14ce1214-b278-a7e4-1373-00cebd1bef7c"}</script>',  # Wix Forms
    ],
)
def test_C137_javascript_form_widget_recognised(widget: str) -> None:
    page = parse_page(TEXT + widget)
    assert has_form(page) and form_place(page, (), "Wix") == HOME


def test_C137_widget_on_top_of_home_is_on_top() -> None:
    page = parse_page('<h1>Plombier</h1><div class="nf-form-cont"></div>' + TEXT)
    assert form_place(page, (), None) == HOME_TOP


def test_C137_look_alike_classes_are_not_forms() -> None:
    page = parse_page(TEXT + '<div class="new-form-banner preview-form"></div>')
    assert not has_form(page) and form_place(page, (), None) == NONE
