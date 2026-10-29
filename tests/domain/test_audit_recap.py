"""C136 : le résultat de l'audit du site, résumé en une ligne pour chaque prospect."""

from prospection.domain.audit_recap import audit_recap
from prospection.domain.page_speed import PageSpeed
from prospection.domain.site_audit import Audit
from prospection.domain.site_report import SiteReport

PROBLEMS = (
    "Pas de HTTPS",
    "Pas adapté au mobile",
    "Ancien Google Analytics, arrêté en juillet 2023 : plus aucune statistique",
    "Pas de formulaire de contact",
)
WEAK = Audit(35, PROBLEMS, "Wix", https=False, mobile=False, contact_form=False)


def test_C136_main_problems_in_one_line() -> None:
    report = SiteReport("fiche Google", "http://a.fr", audit=WEAK, speed=PageSpeed(28, 6200, ()))
    assert audit_recap(report) == (
        "Audit : pas de HTTPS · pas adapté au mobile · ancien Google Analytics, arrêté en "
        "juillet 2023 · +1 autre · lent sur mobile (28/100)"
    )


def test_C136_clean_site_and_unread_site_said_plainly() -> None:
    good = Audit(92, (), "WordPress", https=True, mobile=True, contact_form=True)
    assert audit_recap(SiteReport("fiche Google", "https://a.fr", audit=good)) == (
        "Audit : aucun problème relevé"
    )
    assert audit_recap(SiteReport("fiche Google", problem="Site injoignable")) == (
        "Audit : site injoignable"
    )
    assert audit_recap(SiteReport("aucun")) is None  # sans site : la raison le dit déjà
    assert audit_recap(None) is None
    parked = SiteReport("fiche Google", problem="Page en construction", parked=True)
    assert audit_recap(parked) is None  # « page en construction » est déjà la raison
