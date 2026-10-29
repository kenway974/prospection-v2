"""C57 à C60 : score d'opportunité expliqué, raison lisible, drapeaux, confiance."""

import dataclasses
from datetime import date

from prospection.domain.opportunity import opportunity
from prospection.domain.qualification import confidence, reason
from prospection.domain.signals import signals_of
from prospection.domain.site_audit import Audit
from prospection.domain.site_report import SiteReport
from tests.domain.test_company import LYON_SAS
from tests.storage.test_campaigns import PLACE

TODAY = date(2026, 10, 27)
WEAK = Audit(40, ("Pas de HTTPS",), "Wix", https=False, mobile=True, contact_form=False)
GOOD = Audit(90, (), "WordPress", https=True, mobile=True, contact_form=True)
YOUNG = dataclasses.replace(LYON_SAS, created=date(2026, 8, 20))


def test_C57_no_site_young_company_few_reviews_scores_high_with_details() -> None:
    place = dataclasses.replace(PLACE, review_count=4)
    s = signals_of(place, SiteReport("aucun"), YOUNG, "sûr", (), TODAY)
    score, details = opportunity(s)
    assert details == [
        ("Aucun site (ni sur la fiche Google, ni retrouvé)", 55),
        ("Très peu d'avis Google (4)", 20),
        ("Entreprise créée il y a 2 mois", 10),
    ]
    assert score == 85


def test_C57_solid_presence_scores_low() -> None:
    place = dataclasses.replace(PLACE, review_count=180, rating=4.8, website="https://a.fr")
    site = SiteReport("fiche Google", "https://a.fr", audit=GOOD)
    score, details = opportunity(signals_of(place, site, None, None, (), TODAY))
    assert ("Beaucoup d'avis Google (180)", -10) in details
    assert ("Présence déjà solide (bon site, beaucoup d'avis bien notés)", -40) in details
    assert score == 0  # 5 - 10 - 40 : ramené à 0


def test_C57_weak_site_and_doubts_counted() -> None:
    place = dataclasses.replace(PLACE, review_count=40, phone=None, website="https://a.fr")
    site = SiteReport("fiche Google", "https://a.fr", audit=WEAK)
    flags = ("Entreprise à confirmer",)
    score, details = opportunity(signals_of(place, site, None, None, flags, TODAY))
    assert ("Site à améliorer (qualité 40/100)", 30) in details
    assert ("Pas de formulaire de contact", 15) in details
    assert ("Pas de téléphone (fiche à compléter)", -25) in details
    assert ("À vérifier : Entreprise à confirmer", -5) in details
    assert score == 15


def test_C58_reason_in_plain_words() -> None:
    place = dataclasses.replace(PLACE, review_count=4, phone="+33612345678")
    s = signals_of(place, SiteReport("aucun"), YOUNG, "sûr", (), TODAY)
    assert reason(s) == "sans site, créée il y a 2 mois, 4 avis, mobile"
    weak = signals_of(dataclasses.replace(PLACE, review_count=1, rating=4.5),
                      SiteReport("fiche Google", "https://a.fr", audit=WEAK), None, None, (),
                      TODAY)  # fmt: skip
    assert reason(weak) == "site faible (40/100), 1 avis (4,5/5), mobile"


def test_C60_confidence_of_each_information() -> None:
    place = dataclasses.replace(PLACE, phone="+33612345678")
    found = SiteReport("retrouvé", "https://atelier.fr", audit=GOOD)
    lines = dict((label, level) for label, _, level in
                 confidence(signals_of(place, found, LYON_SAS, "sûr", (), TODAY)))  # fmt: skip
    assert lines == {"Site": "probable", "Entreprise": "sûr", "Dirigeant": "sûr"}
    # le téléphone a sa fiabilité sur sa propre ligne (une seule fois sur la fiche)
    doubtful = SiteReport("aucun", probable="https://atelier.fr")
    unsure_signals = signals_of(place, doubtful, None, "à confirmer", (), TODAY)
    unsure = {label: level for label, _, level in confidence(unsure_signals)}
    assert unsure["Site"] == "à vérifier" and unsure["Entreprise"] == "à vérifier"


def test_months_never_says_zero() -> None:
    from prospection.domain.signals import months

    assert months(0) == "moins d'un jour" and months(1) == "1 jour"


def test_C59_C60_unsure_company_never_used_as_if_sure() -> None:
    """Rapprochement « à confirmer » : peut-être un homonyme, rien n'en est tiré."""
    from prospection.domain.call_sheet import call_sheet
    from prospection.domain.health import health_lines

    place = dataclasses.replace(PLACE, review_count=4)
    s = signals_of(place, SiteReport("aucun"), YOUNG, "à confirmer", (), TODAY)
    assert s.company is None and s.age_days is None
    assert not any("créée" in label for label, _ in opportunity(s)[1])
    assert "créée" not in reason(s)
    hook = call_sheet(s, "menuisier").hook or ""
    assert "lancé" not in hook
    lines = dict(health_lines(s))
    assert lines["Chiffre d'affaires"] == "entreprise pas trouvée avec certitude"


def test_C93_non_diffusible_company_never_reaches_the_signals() -> None:
    hidden = dataclasses.replace(LYON_SAS, diffusible=False)
    assert signals_of(PLACE, None, hidden, "sûr", (), TODAY).company is None


def test_C131_placeholder_page_named_as_such() -> None:
    place = dataclasses.replace(PLACE, review_count=2, phone=None, website="https://a.fr")
    parked = SiteReport("fiche Google", problem="Page en construction", parked=True)
    assert (
        reason(signals_of(place, parked, None, None, (), TODAY)) == "page en construction, 2 avis"
    )
