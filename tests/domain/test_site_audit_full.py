"""C140 à C142 : audit RGPD, sécurité et contact ; chaque problème garde un code stable."""

from prospection.domain.html_page import parse_page
from prospection.domain.site_audit import audit

TEXT = "<h1>Coiffure Léa</h1><p>" + "coupe " * 250 + "</p>"
LEGAL = '<a href="/mentions-legales">Mentions légales</a>'
PRIVACY = '<a href="/politique-de-confidentialite">Confidentialité</a>'
FORM = '<form><input type="email"><textarea></textarea></form>'
GTM = '<script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>'
AXEPTIO = '<script src="https://static.axept.io/sdk.js"></script>'


def codes(html: str, keywords: tuple[str, ...] = ()) -> tuple[str, ...]:
    page = parse_page(f"<html><body>{html}</body></html>")
    return audit(page, "https://lea.fr", 1, 2026, keywords=keywords).codes


def test_codes_follow_the_problems() -> None:
    report = audit(parse_page("<html></html>"), "http://lea.fr", 1, 2026)
    assert len(report.codes) == len(report.problems) and "no_https" in report.codes


def test_C140_legal_notice_and_privacy_policy() -> None:
    found = codes(TEXT + FORM)
    assert "no_legal_notice" in found and "no_privacy_policy" in found
    assert not {"no_legal_notice", "no_privacy_policy"} & set(codes(TEXT + FORM + LEGAL + PRIVACY))


def test_C140_privacy_policy_needed_only_when_data_is_collected() -> None:
    assert "no_privacy_policy" not in codes(TEXT + LEGAL)


def test_C140_trackers_without_consent_tool() -> None:
    assert "no_cookie_consent" in codes(TEXT + LEGAL + PRIVACY + GTM)
    assert "no_cookie_consent" not in codes(TEXT + LEGAL + PRIVACY + GTM + AXEPTIO)
    consent_mode = "<script>gtag('consent', 'default', {});</script>"
    assert "no_cookie_consent" not in codes(TEXT + GTM + consent_mode)


def test_C141_broken_https_and_form_sent_in_clear() -> None:
    report = audit(parse_page(TEXT + FORM), "http://lea.fr", 1, 2026, https_failed=True)
    assert "https_broken" in report.codes and "no_https" not in report.codes
    assert (
        "Pas de HTTPS (ou certificat invalide) : les messages du formulaire circulent en clair"
        in report.problems
    )
    clear = audit(parse_page(TEXT + FORM), "http://lea.fr", 1, 2026)
    assert "Pas de HTTPS : les messages du formulaire circulent en clair" in clear.problems


def test_C142_phone_shown_but_not_clickable() -> None:
    assert "phone_not_clickable" in codes(TEXT + "<p>Tél. 04 78 12 34 56</p>")
    linked = '<a href="tel:+33478123456">04 78 12 34 56</a>'
    assert "phone_not_clickable" not in codes(TEXT + linked)


def test_C142_online_booking_only_for_trades_where_it_counts() -> None:
    assert "no_booking" in codes(TEXT, keywords=("coiffeur",))
    assert "no_booking" not in codes(TEXT, keywords=("plombier",))
    planity = '<a href="https://www.planity.com/coiffure-lea">Réserver</a>'
    assert "no_booking" not in codes(TEXT + planity, keywords=("coiffeur",))
    assert "no_booking" not in codes(TEXT + '<a href="/rdv">Prendre rendez-vous</a>',
                                     keywords=("salon de coiffure",))  # fmt: skip
