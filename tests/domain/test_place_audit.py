"""C161 : audit de la fiche Google (avis, note, horaires, photos, site)."""

import dataclasses
from typing import Any

from prospection.domain.place_audit import place_findings
from tests.storage.test_campaigns import PLACE

GOOD = dataclasses.replace(PLACE, rating=4.7, review_count=48, opening_hours=("lundi : 8h-18h",),
                           photo_count=10, website="https://p.fr")  # fmt: skip


def codes(**changes: Any) -> list[str]:
    return [code for code, _, _ in place_findings(dataclasses.replace(GOOD, **changes), False)]


def test_C161_good_listing_has_nothing_to_say() -> None:
    assert codes() == []


def test_C161_each_weak_point_said() -> None:
    assert codes(review_count=4) == ["gmb_few_reviews"]
    assert codes(rating=3.6) == ["gmb_low_rating"]
    assert codes(rating=3.6, review_count=3) == ["gmb_few_reviews"]  # note pas significative
    assert codes(opening_hours=()) == ["gmb_no_hours"]
    assert codes(photo_count=2) == ["gmb_few_photos"]


def test_C161_no_site_when_none_found() -> None:
    no_site = dataclasses.replace(GOOD, website=None)
    assert [c for c, _, _ in place_findings(no_site, True)] == ["no_site"]
    assert place_findings(no_site, False) == []  # site retrouvé ailleurs


def test_C161_texts_are_plain_french() -> None:
    texts = [t for _, t, _ in place_findings(dataclasses.replace(GOOD, review_count=4), False)]
    assert texts == ["Peu d'avis sur la fiche Google (4)"]


def test_C161_company_without_google_listing_is_not_judged() -> None:
    bare = dataclasses.replace(GOOD, place_id="siren:912345678", review_count=0, rating=None)
    assert place_findings(bare, True) == []
