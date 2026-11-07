"""C160 : accroche personnalisée tirée des faits connus, selon le métier."""

from datetime import date

from prospection.domain.mail_hooks import LeadFacts, matching_hooks

TODAY = date(2026, 11, 7)
FACTS = LeadFacts("Martin Paysage", 4.8, 52, None, (), True, TODAY)


def test_C160_great_reviews_make_the_hook() -> None:
    hooks = matching_hooks(FACTS, ("paysagiste",))
    assert (
        hooks[0] == "4,8 ★ sur 52 avis Google : vos clients sont ravis, votre site doit le montrer."
    )


def test_C160_new_company_congratulated() -> None:
    facts = LeadFacts("Martin Paysage", None, 0, date(2026, 6, 1), (), True, TODAY)
    assert matching_hooks(facts, ())[0] == "Félicitations pour le lancement de Martin Paysage !"


def test_C160_rge_label_for_building_trades() -> None:
    facts = LeadFacts("AZ Énergie", None, 0, None, ("est_rge",), True, TODAY)
    assert "RGE" in matching_hooks(facts, ("plombier chauffagiste",))[0]
    assert all("RGE" not in h for h in matching_hooks(facts, ("restaurant",)))


def test_C160_no_site_wording_and_nothing_when_no_fact() -> None:
    facts = LeadFacts("Martin", 4.9, 30, None, (), False, TODAY)
    assert matching_hooks(facts, ())[0].endswith("un site les ferait venir encore plus.")
    assert matching_hooks(LeadFacts("X", None, 0, None, (), True, TODAY), ()) == []
