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
