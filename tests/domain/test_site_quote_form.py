"""C167 : chaque métier ciblé doit avoir une demande de devis complète, avec les questions
d'une première estimation, plutôt qu'un simple formulaire de contact."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit
from prospection.domain.site_form_quality import missing_questions
from prospection.domain.site_signals import signals

TARGETED = (
    "électricien", "plombier", "couvreur", "menuiserie aluminium", "cuisiniste", "salle de bain",
    "pisciniste", "installateur photovoltaïque", "isolation des combles", "salle de mariage",
    "photographe de mariage", "gîte", "hôtel", "auto-école", "centre de formation",
    "courtier en crédit", "agence immobilière", "expert-comptable", "cabinet d'avocats",
    "diagnostiqueur immobilier", "dératisation", "ramonage", "coach sportif", "micro-crèche",
    "wedding planner", "location de matériel événementiel",
)  # fmt: skip
CONSENT = '<input type="checkbox" name="rgpd"> politique de confidentialité'


def _form(*fields: str) -> str:
    return (f'<form><input name="nom"><input type="email" name="email">{"".join(fields)}'
            f"<textarea name='message'></textarea>{CONSENT}</form>")  # fmt: skip


def _report(form: str, trade: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    page = parse_page("<h1>Accueil</h1>" + form + "<p>" + "texte " * 300 + "</p>")
    report = audit(page, "https://p.fr", 1, 2026, keywords=(trade,))
    return report.codes, report.problems


def test_C167_landscaper_quote_form_without_estimate_questions() -> None:
    form = _form('<select name="prestation"></select>', '<input name="ville">')
    codes, problems = _report(form, "paysagiste")
    assert "quote_incomplete" in codes
    text = next(p for p in problems if p.startswith("Formulaire de demande incomplet"))
    assert "surface" in text and "végétation" in text


def test_C167_complete_landscaper_quote_form_is_not_flagged() -> None:
    form = _form('<input name="surface">', '<select name="prestation"></select>',
                 '<input name="vegetation" placeholder="Végétation présente">',
                 '<input type="file" name="photos">', '<input name="code_postal">')  # fmt: skip
    assert "quote_incomplete" not in _report(form, "paysagiste")[0]


def test_C167_heating_needs_house_questions() -> None:
    form = _form('<select name="type_projet"></select>', '<input name="code_postal">')
    missing = _missing(form, "pompe à chaleur")
    assert {"surface du logement", "chauffage actuel", "état du logement"} <= set(missing)


def test_C167_caterer_needs_guests_and_dishes_not_restaurant_booking() -> None:
    form = _form('<input type="date" name="date">', '<select name="prestation"></select>')
    missing = _missing(form, "traiteur")
    assert "nombre de couverts" in missing and "choix des plats" in missing


def test_C167_every_targeted_sector_has_its_questions() -> None:
    for trade in TARGETED:
        assert _missing(_form(), trade), trade


def test_C167_specific_groups_come_before_generic_ones() -> None:
    names = list(signals().form_expectations)
    assert names.index("traiteur") < names.index("restauration")
    assert names.index("cvc") < names.index("batiment")


def _missing(form: str, trade: str) -> list[str]:
    summary = parse_page(form).best_form
    assert summary is not None
    return missing_questions(summary, (trade,), limit=10)
