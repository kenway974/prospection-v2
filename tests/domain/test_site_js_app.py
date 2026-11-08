"""C152 : un site affiché seulement par JavaScript n'est jamais jugé sans texte ni sans
formulaire ; l'audit dit que son contenu est à vérifier à la main."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit
from prospection.domain.site_form import UNKNOWN

BASE44 = """<!doctype html><html lang="fr"><head><title>VG Paysagiste</title>
<meta name="viewport" content="width=device-width"><meta name="description" content="Paysagiste">
<script type="module" crossorigin src="/assets/index-Bx12.js"></script></head>
<body><div id="root"></div></body></html>"""


def test_C152_javascript_app_is_not_judged_on_empty_html() -> None:
    report = audit(parse_page(BASE44), "https://vg-paysagiste.base44.app/", 1, 2026,
                   keywords=("paysagiste",))  # fmt: skip
    assert report.form_place == UNKNOWN
    for wrong in ("no_form", "thin_content", "no_h1", "no_legal_notice", "phone_not_clickable",
                  "no_social"):  # fmt: skip
        assert wrong not in report.codes, wrong
    assert "js_only" in report.codes
    assert any("JavaScript" in p for p in report.problems)
    assert report.technology == "Base44"


def test_C152_normal_page_with_little_text_is_still_thin() -> None:
    page = parse_page('<html><body><div id="root"><h1>Paysagiste</h1><p>Bonjour</p></div>'
                      '<script src="/app.js"></script></body></html>')  # fmt: skip
    report = audit(page, "https://p.fr", 1, 2026)
    assert "thin_content" in report.codes and "js_only" not in report.codes


# Base44 (novembre 2026) : un résumé caché pour Google, dans la racine de l'application.
BASE44_SNAPSHOT = """<!DOCTYPE html><html lang="en"><head>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Vincent Jardinier - Votre Expert Paysagiste à Montpellier</title>
<script crossorigin="" src="/assets/index-D7I5-Vmr.js" type="module"></script></head>
<body><div id="root"><div data-seo-source="builder" id="seo-snapshot" style="position:absolute;
width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)"><main><header>
<h1>Vincent Jardinier - Votre Expert Paysagiste à Montpellier</h1>
<p>Le site officiel de Vincent Gontier, jardinier professionnel à Montpellier. Découvrez nos
services d'entretien, taille, création de massifs et plus encore. Demandez votre devis gratuit
et bénéficiez de 50% de réduction fiscale. Fiabilité, professionnalisme et passion au cœur de
chaque jardin.</p></header><nav aria-label="Pages"><h2>Pages</h2><ul>
<li><a href="/Apropos">Apropos</a></li><li><a href="/Contact">Contact</a></li>
<li><a href="/Realisations">Realisations</a></li><li><a href="/Services">Services</a></li>
</ul></nav></main></div></div></body></html>"""


def test_C166_hidden_seo_snapshot_is_still_a_javascript_site() -> None:
    """Le résumé caché ne montre ni formulaire ni mentions légales : la page reste à lire
    avec un navigateur (vg-paysagiste.base44.app, 08/11/2026)."""
    report = audit(parse_page(BASE44_SNAPSHOT), "https://vg-paysagiste.base44.app/", 1, 2026,
                   keywords=("paysagiste",))  # fmt: skip
    assert "js_only" in report.codes
    assert "no_form" not in report.codes and "no_legal_notice" not in report.codes
