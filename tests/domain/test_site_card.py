"""C46 à C52 : bloc « Le site » de la fiche, en clair."""

from prospection.domain.site_audit import Audit
from prospection.domain.site_card import site_lines, site_links
from prospection.domain.site_contacts import Contacts
from prospection.domain.site_report import SiteReport
from prospection.domain.site_seo import LocalSeo

AUDIT = Audit(55, ("Pas de HTTPS", "Pas de formulaire de contact"), "Wix", False, True, False)
SEO = LocalSeo({}, {}, ("La ville n'apparaît ni dans le titre ni dans le H1",))
CONTACTS = Contacts(("contact@martin.fr",), ("+33478123456",),
                    ("https://www.facebook.com/martin", "javascript:alert(1)"))  # fmt: skip


def test_C52_audited_site_in_plain_words() -> None:
    report = SiteReport("retrouvé", "http://martin.fr", audit=AUDIT, seo=SEO, contacts=CONTACTS)
    assert site_lines(report) == [
        ("Origine", "Retrouvé à partir du nom (absent de la fiche Google)"),
        ("Score", "55/100"), ("Technologie", "Wix"),
        ("Problèmes", "Pas de HTTPS ; Pas de formulaire de contact"),
        ("SEO local", "La ville n'apparaît ni dans le titre ni dans le H1"),
        ("Emails", "contact@martin.fr"), ("Téléphones", "04 78 12 34 56"),
    ]  # fmt: skip
    assert site_links(report) == [
        ("Site web", "http://martin.fr"),
        ("Facebook", "https://www.facebook.com/martin"),
    ]  # lien dangereux écarté


def test_site_states_said_plainly() -> None:
    assert site_lines(None) == [("Site", "Pas encore analysé.")]
    assert site_lines(SiteReport("aucun")) == [("Site", "Aucun site trouvé.")]
    probable = SiteReport("aucun", probable="https://martin.fr")
    assert site_lines(probable) == [("Site", "Site probable, à confirmer (homonyme possible).")]
    assert site_links(probable) == [("Site probable", "https://martin.fr")]
    down = SiteReport("fiche Google", problem="Site injoignable")
    assert site_lines(down) == [("Site", "Site injoignable")]


def test_C139_form_place_shown() -> None:
    audit = Audit(80, (), "WordPress", True, True, True, "sur une page Contact")
    lines = site_lines(SiteReport("fiche Google", "https://m.fr", audit=audit))
    assert ("Formulaire", "sur une page Contact") in lines
