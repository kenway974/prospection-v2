"""Bloc « Le site » de la fiche : ce que dit l'analyse du site, en clair (C46 à C52)."""

from urllib.parse import urlsplit

import phonenumbers

from prospection.domain.page_speed import issue_labels, speed_line
from prospection.domain.place import web_link
from prospection.domain.site_report import SiteReport

ORIGINS = {
    "fiche Google": "Fiche Google",
    "retrouvé": "Retrouvé à partir du nom (absent de la fiche Google)",
}
_NETWORKS = {"facebook.com": "Facebook", "instagram.com": "Instagram", "linkedin.com": "LinkedIn"}


def _national(number: str) -> str:
    try:
        parsed = phonenumbers.parse(number, None)
    except phonenumbers.NumberParseException:
        return number
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)


def site_lines(report: SiteReport | None) -> list[tuple[str, str]]:
    """Lignes du bloc ; jamais rien d'inventé."""
    if report is None:
        return [("Site", "Pas encore analysé.")]
    if report.audit is None:
        if report.problem:
            return [("Site", report.problem)]
        if report.probable:
            return [("Site", "Site probable, à confirmer (homonyme possible).")]
        return [("Site", "Aucun site trouvé.")]
    audit, lines = report.audit, [("Origine", ORIGINS.get(report.origin, report.origin))]
    lines += [("Score", f"{audit.score}/100"), ("Technologie", audit.technology or "inconnue"),
              ("Problèmes", " ; ".join(audit.problems) or "aucun")]  # fmt: skip
    if audit.form_place:
        lines.append(("Formulaire", audit.form_place))
    if report.seo:
        lines.append(
            ("SEO local", " ; ".join(report.seo.problems) or "métier et ville bien placés")
        )
    if report.speed:
        lines.append(("Vitesse mobile (Google)", speed_line(report.speed)))
        if issues := issue_labels(report.speed):
            lines.append(("À améliorer", " ; ".join(issues)))
    contacts = report.contacts
    if contacts and contacts.emails:
        lines.append(("Emails", ", ".join(contacts.emails)))
    if contacts and contacts.phones:
        lines.append(("Téléphones", ", ".join(_national(p) for p in contacts.phones)))
    return lines


def _network(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return next((name for domain, name in _NETWORKS.items() if host.endswith(domain)), "Réseau")


def site_links(report: SiteReport | None) -> list[tuple[str, str]]:
    """Liens à ouvrir, chacun revalidé (http(s) complet seulement, règle 5)."""
    if report is None:
        return []
    links = []
    if report.url and (url := web_link(report.url)):
        links.append(("Site web", url))
    if report.probable and (url := web_link(report.probable)):
        links.append(("Site probable", url))
    for social in report.contacts.social if report.contacts else ():
        if url := web_link(social):
            links.append((_network(url), url))
    return links
