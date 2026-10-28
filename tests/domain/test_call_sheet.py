"""C110, C111 : fiche « Pour l'appel » par règles fixes, douleurs à confirmer."""

import dataclasses
from datetime import date

import pytest

from prospection.domain.call_sheet import CONFIRM, InvalidRules, call_sheet, parse_rules
from prospection.domain.signals import signals_of
from prospection.domain.site_audit import Audit
from prospection.domain.site_report import SiteReport
from tests.domain.test_company import LYON_SAS
from tests.storage.test_campaigns import PLACE

TODAY = date(2026, 10, 27)
WEAK = Audit(40, ("Pas de HTTPS",), "Wix", https=False, mobile=False, contact_form=False)


def test_C110_no_site_gives_hook_and_pains_with_variables() -> None:
    place = dataclasses.replace(PLACE, name="Atelier Bois", address="3 rue X, 69003 Lyon",
                                review_count=3)  # fmt: skip
    young = dataclasses.replace(LYON_SAS, created=date(2026, 8, 20))
    sheet = call_sheet(signals_of(place, SiteReport("aucun"), young, "sûr", (), TODAY),
                       "menuisier")  # fmt: skip
    assert sheet.hook is not None and "Atelier Bois" in sheet.hook
    assert 1 <= len(sheet.pains) <= 3
    assert sheet.notice == CONFIRM == "Indices à confirmer pendant l'appel, jamais des certitudes."


def test_C110_weak_site_pains_ordered_by_priority() -> None:
    place = dataclasses.replace(PLACE, website="http://a.fr", review_count=50, rating=4.6)
    site = SiteReport("fiche Google", "http://a.fr", audit=WEAK)
    sheet = call_sheet(signals_of(place, site, None, None, (), TODAY), "plombier")
    assert len(sheet.pains) == 3
    assert any("mobile" in p for p in sheet.pains)


def test_C111_nothing_matches_says_so() -> None:
    from prospection.domain.site_seo import LocalSeo

    good = Audit(95, (), "WordPress", True, True, True)
    site = SiteReport("fiche Google", "https://a.fr", audit=good,
                      seo=LocalSeo({}, {}, ()))  # fmt: skip
    place = dataclasses.replace(PLACE, website="https://a.fr", review_count=300, rating=4.9,
                                opening_hours=("lundi: 08:00-18:00",))  # fmt: skip
    sheet = call_sheet(signals_of(place, site, None, None, (), TODAY), "plombier")
    assert sheet.hook is None and sheet.pains == ()


@pytest.mark.parametrize(
    "text",
    ["rules: [{id: x, priority: 1, when: {inconnu: true}, pains: [a]}]",
     "rules: [{id: x, priority: 1, when: {has_site: false}, hook: 'Bonjour {inconnu}'}]",
     "rules: [{id: x, priority: 1, when: {}, pains: [a]}]", "rules: 3",
     "rules: [{id: x, priority: 1, when: {has_site: false}, hook: '{nom!z}'}]",
     "rules: [{id: x, priority: 1, when: {has_site: false}, hook: '{nom:d}'}]",
     "rules: [{id: x, priority: 1, when: {has_site: false}, hook: '{nom:>999999999}'}]",
     "rules: [{id: x, priority: 1, when: {has_site: false}, hook: 'a {'}]",
     "rules: [{id: x, priority: 1, when: {has_site: false}, pains: [a]},"
     " {id: x, priority: 2, when: {no_hours: true}, pains: [b]}]"],
)  # fmt: skip
def test_C110_invalid_rule_file_refused(text: str) -> None:
    with pytest.raises(InvalidRules):
        parse_rules(text)


def test_C111_probable_site_never_called_absent() -> None:
    """Site probable (homonyme possible) : on ne dit pas « pas de site »."""
    place = dataclasses.replace(PLACE, review_count=50)
    site = SiteReport("aucun", probable="https://atelier.fr")
    sheet = call_sheet(signals_of(place, site, None, None, (), TODAY), "menuisier")
    assert sheet.hook is None or "pas de site" not in sheet.hook


def test_C111_texts_are_hints_not_certainties() -> None:
    """Chaque accroche et douleur du fichier livré est une hypothèse, pas une affirmation."""
    from prospection.domain.call_sheet import load_rules

    hedges = ("peut-être", "sans doute", "semble", "souvent", "risque", "parfois", "?")
    for rule in load_rules():
        for text in (rule.hook or "", *rule.pains):
            if text:
                assert any(h in text.lower() for h in hedges), (rule.id, text)


def test_C57_C110_site_down_is_an_opportunity() -> None:
    from prospection.domain.opportunity import opportunity

    place = dataclasses.replace(PLACE, website="https://a.fr", review_count=50)
    down = SiteReport("fiche Google", problem="Site injoignable")
    s = signals_of(place, down, None, None, (), TODAY)
    assert ("Site injoignable ou illisible", 40) in opportunity(s)[1]
    sheet = call_sheet(s, "plombier")
    assert sheet.hook is not None and "répondre" in sheet.hook


def test_rule_with_an_unknown_value_is_skipped() -> None:
    """Une règle qui cite l'ancienneté ne s'affiche pas quand elle est inconnue."""
    rules = parse_rules(
        "rules: [{id: x, priority: 1, when: {no_hours: true}, hook: 'Créée il y a {ancienneté}'}]"
    )
    sheet = call_sheet(signals_of(PLACE, None, None, None, (), TODAY), "plombier", rules)
    assert sheet.hook is None
