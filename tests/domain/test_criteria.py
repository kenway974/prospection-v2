"""C19 à C23, C30, C31, C33 : critères de qualification d'un établissement."""

from dataclasses import replace

from prospection.domain.criteria import Criteria, Exclusions, Verdict, evaluate
from prospection.domain.place import Place
from prospection.domain.trades import find_trade, load_trades

TRADES = load_trades()
CUISINISTE = find_trade("cuisiniste", TRADES)
FLEURISTE = find_trade("fleuriste", TRADES)
NONE = Exclusions(frozenset(), frozenset(), frozenset())
PLACE = Place(
    place_id="p1", name="Atelier Cuisine Hoarau", address="Saint-Denis", lat=None, lon=None,
    types=("furniture_store",), primary_type="furniture_store", business_status="OPERATIONAL",
    phone="+262 692 12 34 56", website=None, rating=4.8, review_count=4, opening_hours=(),
    maps_url=None, photo_count=0, owner_photo_estimate="inconnu",
)  # fmt: skip


DEFAULT = Criteria()


def check(
    place: Place = PLACE, criteria: Criteria = DEFAULT, exclusions: Exclusions = NONE
) -> Verdict:
    return evaluate(place, CUISINISTE, criteria, exclusions)


def test_qualified_by_default() -> None:
    verdict = check()
    assert verdict.qualified is True and verdict.reasons == ()


def test_C19_review_bounds() -> None:
    assert check(replace(PLACE, review_count=31)).reasons == ("Trop d'avis (31)",)
    low = check(criteria=Criteria(min_reviews=5))
    assert low.reasons == ("Pas assez d'avis (4)",)


def test_C20_no_rating_is_not_excluded() -> None:
    assert check(replace(PLACE, rating=None, review_count=0)).qualified is True


def test_C21_website_criterion() -> None:
    with_site = replace(PLACE, website="https://exemple.fr")
    assert check(with_site, Criteria(website="without")).reasons == ("Avec site",)
    assert check(PLACE, Criteria(website="with")).reasons == ("Sans site",)
    assert check(with_site, Criteria(website="any")).qualified is True


def test_C22_phone_criterion() -> None:
    landline = replace(PLACE, phone="+262 262 21 00 00")
    assert check(landline, Criteria(phone="mobile")).reasons == ("Pas de mobile",)
    assert check(replace(PLACE, phone=None)).reasons == ("Sans téléphone",)
    assert check(PLACE, Criteria(phone="mobile")).qualified is True


def test_C23_off_trade_category_excluded() -> None:
    restaurant = replace(PLACE, name="Chez Marcel", types=("restaurant", "food"))
    assert check(restaurant).reasons == ("Hors métier (food, restaurant)",)


def test_C23_unconfirmed_trade_kept_but_to_check() -> None:
    unclear = replace(PLACE, name="Hoarau et fils", types=("store",))
    verdict = check(unclear)
    assert verdict.qualified is True
    assert verdict.to_check == ("Métier « Cuisiniste » non confirmé",)


def test_C30_franchise_from_list_and_personal_list_excluded() -> None:
    assert check(replace(PLACE, name="Cuisinella Saint-Denis")).reasons == (
        "Franchise ou chaîne (cuisinella)",
    )
    mine = Exclusions(frozenset({"atelier cuisine hoarau"}), frozenset(), frozenset())
    assert check(exclusions=mine).reasons == ("Franchise ou chaîne (atelier cuisine hoarau)",)
    assert check(replace(PLACE, name="Cuisinella"), Criteria(exclude_franchises=False)).qualified


def test_C31_independent_with_brand_like_name_marked_to_check() -> None:
    paul = replace(PLACE, name="Boulangerie Paul Hoarau", types=("bakery",))
    verdict = evaluate(paul, find_trade("boulangerie", TRADES), Criteria(), NONE)
    assert verdict.qualified is True
    assert verdict.to_check == ("Nom proche de l'enseigne « paul »",)
    exact = evaluate(
        replace(paul, name="PAUL"), find_trade("boulangerie", TRADES), Criteria(), NONE
    )
    assert exact.reasons == ("Franchise ou chaîne (paul)",)


def test_C33_blacklist_excluded() -> None:
    by_id = Exclusions(frozenset(), frozenset({"p1"}), frozenset())
    by_name = Exclusions(frozenset(), frozenset(), frozenset({"atelier cuisine hoarau"}))
    assert check(exclusions=by_id).reasons == ("Liste noire",)
    assert check(exclusions=by_name).reasons == ("Liste noire",)


def test_closed_permanently_excluded() -> None:
    closed = replace(PLACE, business_status="CLOSED_PERMANENTLY")
    assert check(closed).reasons[0] == "Fermé définitivement"


def test_unknown_trade_skips_category_check() -> None:
    odd = replace(PLACE, types=("restaurant",))
    assert evaluate(odd, None, Criteria(), NONE).qualified is True


def test_small_shop_family_never_excluded_on_category_alone() -> None:
    shop = replace(PLACE, name="Les Jolies Choses", types=("clothing_store",))
    verdict = evaluate(shop, FLEURISTE, Criteria(), NONE)
    assert verdict.qualified is True and verdict.to_check


def test_C32_already_in_crm_excluded() -> None:
    from prospection.domain.criteria import Criteria

    crm = Exclusions(frozenset(), frozenset(), frozenset(), crm_ids=frozenset({"p1"}))
    by_name = Exclusions(frozenset(), frozenset(), frozenset(),
                         crm_names=frozenset({"atelier cuisine hoarau"}))  # fmt: skip
    for exclusions in (crm, by_name):
        verdict = evaluate(PLACE, None, Criteria(phone="any", max_reviews=None), exclusions)
        assert "Déjà dans le CRM" in verdict.reasons
