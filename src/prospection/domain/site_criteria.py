"""Critères sur le site, appliqués après sa lecture (C28, C29).

Hypothèse (écrite, à valider) : sans site lisible (aucun site, ou site injoignable), un
établissement n'est jamais écarté par ces critères : le besoin est encore plus fort.
Un site retrouvé (absent de la fiche Google) compte pour « avec site » / « sans site ».
"""

from prospection.domain.criteria import Criteria
from prospection.domain.site_report import SiteReport

SITE_CHOICES = ("any", "only", "exclude")
# (critère, raison si exclu car il a ce défaut, raison si exclu car il ne l'a pas)
_PROBLEMS = (
    ("no_form", "Site sans formulaire de contact", "Site avec formulaire de contact"),
    ("no_https", "Site sans HTTPS", "Site en HTTPS"),
    ("not_mobile", "Site pas adapté au mobile", "Site adapté au mobile"),
)


def site_reasons(report: SiteReport, criteria: Criteria) -> list[str]:
    reasons = []
    if criteria.website == "without" and report.origin == "retrouvé":
        reasons.append("Avec site (retrouvé)")
    if criteria.website == "with" and report.url is None and report.origin == "aucun":
        reasons.append("Sans site")
    audit = report.audit
    if audit is None:
        return reasons
    if criteria.max_site_score is not None and audit.score > criteria.max_site_score:
        reasons.append(f"Site correct ({audit.score}/100)")
    has = {"no_form": not audit.contact_form, "no_https": not audit.https,
           "not_mobile": not audit.mobile}  # fmt: skip
    for field, with_problem, without_problem in _PROBLEMS:
        choice = getattr(criteria, field)
        if choice == "exclude" and has[field]:
            reasons.append(with_problem)
        elif choice == "only" and not has[field]:
            reasons.append(without_problem)
    return reasons


def site_criteria_errors(criteria: Criteria) -> dict[str, str]:
    errors = {}
    score = criteria.max_site_score
    if score is not None and not 1 <= score <= 100:
        errors["max_site_score"] = "Choisissez un score entre 1 et 100, ou laissez vide."
    if any(getattr(criteria, field) not in SITE_CHOICES for field, *_ in _PROBLEMS):
        errors["site_problems"] = "Choisissez une option dans la liste pour chaque défaut du site."
    return errors
