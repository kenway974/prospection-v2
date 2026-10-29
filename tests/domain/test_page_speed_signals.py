"""Un site lent sur mobile (PageSpeed) : fiche, score d'opportunité, « Pour l'appel »."""

import dataclasses
from datetime import date

from prospection.domain.call_sheet import call_sheet
from prospection.domain.opportunity import opportunity
from prospection.domain.page_speed import PageSpeed
from prospection.domain.signals import signals_of
from prospection.domain.site_audit import Audit
from prospection.domain.site_card import site_lines
from prospection.domain.site_report import SiteReport
from tests.storage.test_campaigns import PLACE

TODAY = date(2026, 10, 29)
GOOD = Audit(85, (), "WordPress", https=True, mobile=True, contact_form=True)
SLOW = PageSpeed(31, 7400, ("uses-optimized-images", "render-blocking-resources"))


def site(speed: PageSpeed | None) -> SiteReport:
    return SiteReport("fiche Google", url="https://a.fr", audit=GOOD, speed=speed)


def test_slow_site_shown_scored_and_used_as_hook() -> None:
    place = dataclasses.replace(PLACE, website="https://a.fr", review_count=50)
    lines = dict(site_lines(site(SLOW)))
    assert lines["Vitesse mobile (Google)"] == "31/100 · contenu affiché en 7,4 s"
    assert lines["À améliorer"].startswith("Images trop lourdes")
    s = signals_of(place, site(SLOW), None, None, (), TODAY)
    assert ("Site lent sur mobile (Google : 31/100)", 15) in opportunity(s)[1]
    sheet = call_sheet(s, "boulanger")
    assert sheet.hook is not None and "outil de Google" in sheet.hook


def test_fast_or_unmeasured_site_changes_nothing() -> None:
    place = dataclasses.replace(PLACE, website="https://a.fr", review_count=50)
    for speed in (None, PageSpeed(92, 1500, ())):
        s = signals_of(place, site(speed), None, None, (), TODAY)
        assert not any("lent" in label for label, _ in opportunity(s)[1])
        assert "outil de Google" not in (call_sheet(s, "boulanger").hook or "")
    assert "Vitesse mobile (Google)" not in dict(site_lines(site(None)))
