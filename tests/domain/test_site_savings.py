"""C165 : l'audit propose un simulateur adapté au métier quand le site n'en a pas."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit
from prospection.domain.site_savings import savings_findings


def _codes(body: str, keywords: tuple[str, ...] = ()) -> list[str]:
    return [code for code, _, _ in savings_findings(parse_page(body), keywords)]


def test_C165_approved_home_service_gets_tax_credit_simulator() -> None:
    body = "<p>Entreprise agréée services à la personne : 50 % de crédit d'impôt.</p>"
    assert _codes(body, ("paysagiste",)) == ["sim_sap"]


def test_C165_aid_is_only_cited_when_the_site_mentions_it() -> None:
    assert _codes("<p>Entretien de jardins et tonte.</p>", ("paysagiste",)) == []
    assert _codes("<p>Installateur RGE, éligible MaPrimeRénov'.</p>", ("chauffagiste",)) == [
        "sim_renov"
    ]


def test_C165_trade_alone_suggests_a_calculation_tool() -> None:
    assert _codes("<p>Votre prêt au meilleur taux.</p>", ("courtier en crédit",)) == ["sim_emprunt"]
    assert _codes("<p>Nos installations.</p>", ("installateur photovoltaïque",)) == ["sim_solaire"]


def test_C165_site_aid_wins_over_trade_tool_and_only_one_is_proposed() -> None:
    body = "<p>Pompe à chaleur avec MaPrimeRénov' et prime énergie.</p>"
    assert _codes(body, ("pompe à chaleur",)) == ["sim_renov"]


def test_C165_no_proposal_when_the_site_already_has_a_simulator() -> None:
    body = "<p>Services à la personne.</p><a href='/simulateur'>Simulez votre crédit d'impôt</a>"
    assert _codes(body, ("paysagiste",)) == []


def test_C165_unrelated_trade_gets_nothing() -> None:
    assert _codes("<p>Pizzas au feu de bois.</p>", ("pizzeria",)) == []


def test_C165_never_judged_on_a_javascript_shell() -> None:
    shell = parse_page('<html><head><script src="/a.js"></script></head>'
                       '<body><div id="root"></div></body></html>')  # fmt: skip
    report = audit(shell, "https://x.base44.app/", 1, 2026, keywords=("courtier en crédit",))
    assert not any(code.startswith("sim_") for code in report.codes)


def test_C165_audit_includes_the_proposal() -> None:
    body = "<p>Agrément services à la personne, avance immédiate.</p>"
    page = parse_page(f"<html><head><meta name='viewport' content='w'></head><body>{body}</body>")
    report = audit(page, "https://p.fr", 1, 2026, keywords=("entretien de jardin",))
    assert "sim_sap" in report.codes


def test_C165_every_simulator_has_its_mail_point() -> None:
    from prospection.domain.audit_mail_rules import load_mail_rules
    from prospection.domain.site_savings import PREFIX, savings_rules

    points = load_mail_rules().points
    for simulator in savings_rules().simulateurs:
        assert points[PREFIX + simulator.code].groupe == "simulateur"


def test_C165_common_phrases_never_cite_an_aid() -> None:
    """Relecture : expressions courantes, liens et métiers non concernés."""
    assert (
        _codes("<p>Un petit coup de pouce pour votre fête, TVA à 5,5 %.</p>", ("traiteur",)) == []
    )
    cesu = "<p>Paie et social.</p><a href='https://www.cesu.urssaf.fr'>Urssaf</a>"
    assert _codes(cesu, ("expert-comptable",)) == ["sim_charges"]
    assert _codes("<p>Perte d'autonomie : nous venons chez vous.</p>", ("aide à domicile",)) == []
    assert _codes("<p>Prise en charge CPF possible.</p>", ("expert-comptable",)) == ["sim_charges"]


def test_C165_trade_alone_never_names_an_aid() -> None:
    assert _codes("<p>Installation de bornes.</p>", ("borne de recharge",)) == ["sim_borne_cout"]
    assert _codes("<p>Permis B.</p>", ("auto-école",)) == ["sim_permis_cout"]
    assert _codes("<p>Accueil des tout-petits.</p>", ("micro-crèche",)) == []
    assert _codes("<p>Film solaire pour vitrage.</p>", ("film solaire",)) == []


def test_C165_every_aid_is_tied_to_its_trades() -> None:
    from prospection.domain.site_savings import savings_rules

    for simulator in savings_rules().simulateurs:
        assert simulator.metiers, simulator.code


def test_C165_tax_reduction_wording_of_a_gardener_site() -> None:
    """Formule réelle d'un site de jardinier (vg-paysagiste.base44.app)."""
    body = "<p>Demandez votre devis gratuit et bénéficiez de 50% de réduction fiscale.</p>"
    assert _codes(body, ("paysagiste",)) == ["sim_sap"]
