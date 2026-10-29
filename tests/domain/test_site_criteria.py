"""C28, C29 : critères sur le site (score maximum ; formulaire, HTTPS, mobile)."""

import dataclasses

import pytest

from prospection.domain.campaign_request import (
    CityZone,
    InvalidRequest,
    RawRequest,
    validate_request,
)
from prospection.domain.criteria import Criteria
from prospection.domain.site_audit import Audit
from prospection.domain.site_criteria import site_reasons
from prospection.domain.site_report import SiteReport

WEAK = Audit(40, ("Pas de HTTPS",), "Wix", https=False, mobile=True, contact_form=False)
READ = SiteReport("fiche Google", "http://martin.fr", audit=WEAK)
LYON = CityZone("Lyon", "69123", 45.76, 4.83)


def test_C28_only_weak_sites_kept() -> None:
    assert site_reasons(READ, Criteria(max_site_score=50)) == []
    assert site_reasons(READ, Criteria(max_site_score=30)) == ["Site correct (40/100)"]


def test_C29_each_problem_kept_only_or_excluded() -> None:
    assert site_reasons(READ, Criteria(no_form="only", no_https="only")) == []
    assert site_reasons(READ, Criteria(no_form="exclude")) == ["Site sans formulaire de contact"]
    assert site_reasons(READ, Criteria(not_mobile="only")) == ["Site adapté au mobile"]
    assert site_reasons(READ, Criteria(no_https="exclude")) == ["Site sans HTTPS"]


def test_C28_C29_no_readable_site_is_never_excluded_by_site_criteria() -> None:
    """Pas de site, ou site injoignable : le besoin est encore plus fort, on garde."""
    strict = Criteria(max_site_score=10, no_form="only", not_mobile="only")
    assert site_reasons(SiteReport("aucun"), strict) == []
    assert site_reasons(SiteReport("fiche Google", problem="Site injoignable"), strict) == []


def test_found_site_counts_for_with_or_without_site() -> None:
    found = dataclasses.replace(READ, origin="retrouvé")
    assert site_reasons(found, Criteria(website="without")) == ["Avec site (retrouvé)"]
    assert site_reasons(SiteReport("aucun"), Criteria(website="with")) == ["Sans site"]


@pytest.mark.parametrize(
    ("criteria", "field"),
    [(Criteria(max_site_score=0), "max_site_score"), (Criteria(max_site_score=101),
      "max_site_score"), (Criteria(no_form="peut-être"), "site_problems")],  # type: ignore[arg-type]
)  # fmt: skip
def test_C28_C29_choices_validated(criteria: Criteria, field: str) -> None:
    request = RawRequest("Test", ["cuisiniste"], [LYON], 10, criteria, True)
    with pytest.raises(InvalidRequest) as error:
        validate_request(request)
    assert field in error.value.errors


def test_C131_placeholder_page_counts_as_no_site() -> None:
    parked = SiteReport("retrouvé", problem="Page en construction", parked=True)
    assert site_reasons(parked, Criteria(website="without")) == []
    assert site_reasons(parked, Criteria(website="with")) == ["Sans site (page en construction)"]
