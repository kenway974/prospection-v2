"""C166 : un site affiché seulement par JavaScript est relu avec un vrai navigateur, puis
jugé comme un site classique (formulaire, texte, page Contact)."""

import dataclasses

from prospection.application.site_check import check_site
from prospection.application.site_emails import Reader
from prospection.sources.web_reader import ReadResult, WebPage
from tests.application.test_site_check import AZ
from tests.application.test_site_check_contact_page import pages

SITE = "https://vg-paysagiste.base44.app/"
PLACE = dataclasses.replace(AZ, website=SITE)
SHELL = """<!doctype html><html><head><title>VG</title><meta name="viewport" content="w">
<script type="module" src="/assets/index.js"></script></head><body><div id="root"></div></body>
</html>"""
RENDERED_HOME = (
    "<html><head><meta name='viewport' content='w'></head><body><h1>Paysagiste</h1><p>"
    + "jardin " * 200 + "</p><a href='/contact'>Contact</a></body></html>"
)  # fmt: skip
RENDERED_CONTACT = ("<html><body><p>" + "texte " * 300 + "</p><form><input name='nom'>"
                    "<input type='email' name='email'><textarea name='message'></textarea>"
                    "</form></body></html>")  # fmt: skip


def browser(by_url: dict[str, str], seen: list[str]) -> Reader:
    def render(url: str, seconds: float) -> ReadResult:
        seen.append(url)
        html = by_url.get(url)
        return ReadResult(WebPage(url, html, 1.0)) if html else ReadResult(None, "Site injoignable")

    return render


def test_C166_javascript_site_is_judged_on_the_rendered_page() -> None:
    seen: list[str] = []
    render = browser({SITE: RENDERED_HOME, SITE + "contact": RENDERED_CONTACT}, seen)
    report = check_site(pages({"/": SHELL}), PLACE, ("paysagiste",), 2026, browser=render)
    assert report.audit is not None
    assert "js_only" not in report.audit.codes
    assert report.audit.form_place == "sur une page Contact"
    assert {"form_buried", "form_basic"} <= set(report.audit.codes)
    assert seen == [SITE, SITE + "contact"]


def test_C166_browser_failure_keeps_the_cautious_audit() -> None:
    report = check_site(pages({"/": SHELL}), PLACE, ("paysagiste",), 2026,
                        browser=browser({}, []))  # fmt: skip
    assert report.audit is not None and "js_only" in report.audit.codes


def test_C166_classic_site_never_opens_the_browser() -> None:
    seen: list[str] = []
    check_site(pages({"/": RENDERED_HOME}), PLACE, ("paysagiste",), 2026, browser=browser({}, seen))
    assert seen == []
