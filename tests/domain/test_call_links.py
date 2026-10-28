"""C55 : mobile ou fixe ; C56 : lien de recherche LinkedIn du dirigeant (sans lire LinkedIn)."""

from urllib.parse import parse_qs, urlsplit

from prospection.domain.call_links import leader_name, linkedin_search, phone_kind


def test_C55_mobile_or_landline() -> None:
    assert phone_kind("+33612345678", "FR") == "mobile"
    assert phone_kind("04 78 12 34 56", "FR") == "fixe"
    assert phone_kind("0692 12 34 56", "FR") == "mobile"  # La Réunion
    assert phone_kind("n'importe quoi", "FR") == "inconnu"


def test_C56_search_link_only_never_a_profile() -> None:
    url = linkedin_search("Marie DUPONT", "Cuisines Martin")
    parts = urlsplit(url)
    assert (parts.scheme, parts.hostname, parts.path) == (
        "https", "www.linkedin.com", "/search/results/people/")  # fmt: skip
    assert parse_qs(parts.query)["keywords"] == ["Marie DUPONT Cuisines Martin"]


def test_C56_without_leader_the_role_is_searched() -> None:
    url = linkedin_search(None, "Cuisines Martin")
    assert parse_qs(urlsplit(url).query)["keywords"] == ["gérant Cuisines Martin"]


def test_leader_name_without_role_and_companies_skipped() -> None:
    assert leader_name(("Marie DUPONT (Présidente)", "HOLDING M (Associé)")) == "Marie DUPONT"
    assert leader_name(()) is None


def test_C55_type_and_reason_always_agree() -> None:
    """Une seule lecture du numéro : « mobile » dans la raison et la ligne téléphone concordent."""
    from prospection.domain.phones import is_mobile

    for number, country in (("0470 12 34 56", "BE"), ("+352 621 123 456", "LU"),
                            ("0692 12 34 56", "FR"), ("04 78 12 34 56", "FR")):  # fmt: skip
        assert (phone_kind(number, country) == "mobile") == is_mobile(number, country), number
