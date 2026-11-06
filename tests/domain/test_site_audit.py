"""C49, C50, C52 : technologie, audit rapide et score du site, avec la liste des problèmes."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit

RICH_FORM = (  # formulaire de commande : questions du métier (C153)
    '<form><input type="email"><select name="commande"></select>'
    '<input type="date" name="retrait"></form>'
)
GOOD = (
    """<html><head><title>Boulangerie Martin à Lyon</title>
<meta name="viewport" content="width=device-width">
<meta name="description" content="Pain au levain">
<meta name="generator" content="WordPress 6.6">
<script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script></head>
<body><h1>Boulangerie Martin</h1>"""
    + RICH_FORM
    + """
<a href="https://www.facebook.com/boulangeriemartin">Facebook</a>
<a href="/mentions-legales">Mentions légales</a><a href="/confidentialite">Vie privée</a>
<script src="/tarteaucitron/tarteaucitron.js"></script>
<p>"""
    + "pain " * 250
    + "</p><footer>© 2026 Boulangerie Martin</footer></body></html>"
)

POOR = """<html><body><p>Bienvenue</p><footer>Copyright 2019</footer>
<img src="https://static.wixstatic.com/a.png"></body></html>"""


def test_C50_C52_good_site_scores_full_marks() -> None:
    report = audit(parse_page(GOOD), "https://boulangerie-martin.fr", 0.8, current_year=2026)
    assert report.score == 100 and report.problems == ()
    assert report.technology == "WordPress"


def test_C50_C52_poor_site_lists_each_problem_in_plain_words() -> None:
    report = audit(parse_page(POOR), "http://martin.wixsite.com", 4.5, current_year=2026)
    assert report.technology == "Wix"
    assert {
        "Pas de HTTPS",
        "Pas adapté au mobile",
        "Chargement lent (4,5 s)",
        "Pas de titre de page",
        "Pas de description pour Google",
        "Aucun outil de suivi des visites",
        "Site pas mis à jour depuis 2019",
        "Très peu de texte (3 mots)",
        "Pas de titre principal (H1)",
        "Aucun lien vers les réseaux sociaux",
    } <= set(report.problems)
    assert report.score == 0
    assert report.form_place == "non vérifié"  # Wix dessine ses formulaires en JavaScript (C138)


def test_C50_hidden_from_google_is_said() -> None:
    page = parse_page('<html><head><meta name="robots" content="noindex"></head></html>')
    assert "Caché de Google (noindex)" in audit(page, "https://a.fr", 1, 2026).problems


def test_C49_technology_unknown_is_none() -> None:
    assert audit(parse_page("<html></html>"), "https://a.fr", 1, 2026).technology is None


def test_parse_ignores_scripts_and_styles_in_text() -> None:
    page = parse_page("<p>Bonjour</p><script>var x = 'caché';</script><style>p{}</style>")
    assert page.text == "Bonjour"


def test_C50_copyright_range_uses_the_last_year() -> None:
    page = parse_page("<footer>© 2015\u20132026 Martin</footer>")
    assert not any("mis à jour" in p for p in audit(page, "https://a.fr", 1, 2026).problems)


def test_C88_trap_page_parsed_quickly() -> None:
    """Balises jamais fermées et texte entre chacune : la lecture reste linéaire."""
    import time

    trap = "<div>x" * 80_000 + "<title>" + "t" * 10_000
    start = time.perf_counter()
    page = parse_page(trap)
    assert time.perf_counter() - start < 2
    assert len(page.text) <= 100_000 and len(page.title) <= 300


def test_C49_technology_from_resources_not_from_words() -> None:
    """Un mot ou un lien ne suffit pas : on regarde les ressources chargées par la page."""
    talk = parse_page('<p>Nous aimons Drupal et Joomla</p><a href="https://www.wix.com">Wix</a>')
    assert audit(talk, "https://a.fr", 1, 2026).technology is None
    for src, name in (("https://static.wixstatic.com/a.js", "Wix"),
                      ("/sites/default/files/logo.png", "Drupal"),
                      ("https://cdn.shopify.com/s/a.js", "Shopify")):  # fmt: skip
        page = parse_page(f'<script src="{src}"></script>')
        assert audit(page, "https://a.fr", 1, 2026).technology == name
