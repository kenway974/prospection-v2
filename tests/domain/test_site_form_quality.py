"""C158, C159 : formulaire enterré, bouton « Devis » en haut, qualité du formulaire selon le
métier (champs obligatoires, RGPD, questions utiles)."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit

TEXT = "<p>" + "jardin " * 250 + "</p>"
CONTACT = '<a href="/contact">Contact</a>'
QUOTE_TOP = '<h1>Paysagiste</h1><a href="/contact" class="btn">Devis gratuit</a>'
CONSENT = '<input type="checkbox" name="rgpd" required> J\'accepte la politique de confidentialité'
BASIC = (
    f'<form><input name="nom" required><input type="email" required><textarea></textarea>'
    f"{CONSENT}</form>"
)


def codes(
    home: str, contact: str | None = None, keywords: tuple[str, ...] = ("paysagiste",)
) -> tuple[str, ...]:
    others = (parse_page(contact),) if contact else ()
    return audit(parse_page(home), "https://p.fr", 1, 2026, others=others, keywords=keywords).codes


def test_C158_form_at_the_bottom_of_the_contact_page() -> None:
    assert "form_buried" in codes(CONTACT + TEXT, TEXT + BASIC)
    assert "form_buried" not in codes(CONTACT + TEXT, BASIC + TEXT)


def test_C158_quote_button_on_top_of_home() -> None:
    assert "no_cta_top" in codes(CONTACT + TEXT, BASIC)
    assert "no_cta_top" not in codes(QUOTE_TOP + TEXT, BASIC)
    assert "no_cta_top" not in codes("<h1>P</h1>" + BASIC + TEXT)  # formulaire déjà en haut


def test_C159_too_many_required_fields() -> None:
    long_form = (
        "<form>"
        + "".join(f'<input name="c{i}" required>' for i in range(7))
        + (f'<input type="email" required>{CONSENT}</form>')
    )
    assert "form_too_long" in codes("<h1>P</h1>" + long_form + TEXT)
    assert "form_too_long" not in codes("<h1>P</h1>" + BASIC + TEXT)


def test_C159_no_gdpr_mention_in_the_form() -> None:
    bare = '<form><input name="nom"><input type="email"><textarea></textarea></form>'
    assert "form_no_consent" in codes("<h1>P</h1>" + bare + TEXT)
    assert "form_no_consent" not in codes("<h1>P</h1>" + BASIC + TEXT)
    mention = bare.replace(
        "</form>", "Vos données personnelles sont traitées selon notre politique.</form>"
    )
    assert "form_no_consent" not in codes("<h1>P</h1>" + mention + TEXT)


def test_C159_missing_questions_named_for_the_trade() -> None:
    report = audit(parse_page("<h1>P</h1>" + BASIC + TEXT), "https://p.fr", 1, 2026,
                   keywords=("paysagiste",))  # fmt: skip
    basic = next(p for p, c in zip(report.problems, report.codes, strict=True) if c == "form_basic")
    assert "il manque" in basic and "surface" in basic and "végétation" in basic  # C167
    resto = audit(parse_page("<h1>P</h1>" + BASIC + TEXT), "https://p.fr", 1, 2026,
                  keywords=("restaurant",))  # fmt: skip
    basic = next(p for p, c in zip(resto.problems, resto.codes, strict=True) if c == "form_basic")
    assert "nombre de personnes" in basic
