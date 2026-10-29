"""Audit du site, affiné sur de vrais sites de restaurants (Paris 11, octobre 2026) :
formulaire de contact, ancien Google Analytics, page d'hébergeur, signaux d'un site vieilli."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit, is_placeholder
from tests.domain.test_site_audit import GOOD

YEAR = 2026


def problems(html: str, url: str = "https://resto.fr", powered_by: str = "") -> tuple[str, ...]:
    return audit(parse_page(html), url, 0.8, YEAR, powered_by).problems


def test_search_or_login_form_is_not_a_contact_form() -> None:
    search = GOOD.replace('<form><input type="email"></form>',
                          '<form role="search"><input type="search" name="s"></form>'
                          '<form><input name="log"><input type="password"></form>')  # fmt: skip
    assert "Pas de formulaire de contact" in problems(search)
    quote = GOOD.replace(
        '<form><input type="email"></form>',
        '<form><input name="nom"><textarea name="message"></textarea></form>',
    )
    assert "Pas de formulaire de contact" not in problems(quote)


def test_old_google_analytics_counts_as_no_tracking() -> None:
    legacy = GOOD.replace(
        '<script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>',
        "<script>ga('create', 'UA-1234567-1', 'auto');"
        "</script><script src='https://www.google-analytics.com/analytics.js'></script>",
    )
    found = problems(legacy)
    assert "Ancien Google Analytics, arrêté en juillet 2023 : plus aucune statistique" in found
    assert "Aucun outil de suivi des visites" not in found
    assert not any("Analytics" in p for p in problems(GOOD))  # GA4 (G-…) : rien à dire


def test_signs_of_an_ageing_site() -> None:
    old = (
        GOOD.replace('content="WordPress 6.6"', 'content="WordPress 5.3"')
        .replace("<h1>Boulangerie Martin</h1>", "<h1>A</h1><h1>B</h1><h1>C</h1>")
        .replace("</body>", '<img src="http://resto.fr/a.jpg">' * 6 + "</body>")
    )
    found = problems(old, powered_by="PHP/5.6.40")
    assert "WordPress ancien (version 5.3), plus mis à jour" in found
    assert "Serveur PHP ancien (5.6), sans correctifs de sécurité" in found
    assert "Fichiers chargés sans sécurité (http) sur une page https (6)" in found
    assert "Plusieurs titres principaux (3 H1)" in found
    assert "Images sans description (6)" in found
    assert problems(GOOD, powered_by="PHP/8.2.1") == ()


def test_hosting_placeholder_page_is_not_a_site() -> None:
    ovh = (
        """<html><head><title>Site en construction</title>
    <meta name="robots" content="noindex"></head><body><h1>Site en construction</h1>
    <span style="display:none">"""
        + "y1 y2 y3 " * 200
        + "</span></body></html>"
    )
    assert is_placeholder(parse_page(ovh))
    assert is_placeholder(parse_page("<title>Welcome to nginx!</title><p>If you see this page"))
    assert is_placeholder(parse_page("<h1>Ce nom de domaine est à vendre</h1>"))
    assert not is_placeholder(parse_page(GOOD))
    real = GOOD.replace("pain ", "Notre nouvelle carte est en construction, venez goûter ", 1)
    assert not is_placeholder(parse_page(real))  # un vrai site qui en parle n'est pas visé


def test_dead_analytics_gives_a_call_hook() -> None:
    import dataclasses
    from datetime import date

    from prospection.domain.call_sheet import call_sheet
    from prospection.domain.signals import signals_of
    from prospection.domain.site_report import SiteReport
    from tests.storage.test_campaigns import PLACE

    legacy = GOOD.replace(
        '<script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>',
        "<script>ga('create', 'UA-1234567-1', 'auto');</script>",
    )
    report = audit(parse_page(legacy), "https://resto.fr", 0.8, YEAR)
    site = SiteReport("fiche Google", url="https://resto.fr", audit=report)
    place = dataclasses.replace(PLACE, website="https://resto.fr", review_count=300)
    sheet = call_sheet(signals_of(place, site, None, None, (), date(2026, 10, 29)), "restaurant")
    assert sheet.hook is not None and "arrêté en 2023" in sheet.hook
