"""Raison de qualification lisible (C58) et confiance de chaque information (C60)."""

from prospection.domain.signals import Signals, months

SURE, LIKELY, CHECK = "sûr", "probable", "à vérifier"
YOUNG_REASON_DAYS = 3 * 365


def _site_words(s: Signals) -> str:
    audit = s.audit
    if s.site and s.site.parked:  # dit tel quel : c'est l'accroche de l'appel (C131)
        return "page en construction"
    if not s.has_site:
        return "sans site"
    if audit is None:
        return "site non analysé" if not (s.site and s.site.problem) else "site injoignable"
    return f"site {'faible' if audit.score < 60 else 'correct'} ({audit.score}/100)"


def reason(s: Signals) -> str:
    """« sans site, créée il y a 2 mois, 4 avis, mobile »."""
    parts = [_site_words(s)]
    if s.age_days is not None and s.age_days <= YOUNG_REASON_DAYS:
        parts.append(f"créée il y a {months(s.age_days)}")
    count, rating = s.place.review_count, s.place.rating
    note = f" ({f'{rating:.1f}'.replace('.', ',')}/5)" if rating and count else ""
    parts.append(f"{count} avis{note}")
    if s.mobile:
        parts.append("mobile")
    return ", ".join(parts)


def confidence(s: Signals) -> list[tuple[str, str, str]]:
    """(information, valeur, sûr / probable / à vérifier), pour ce qui est connu."""
    lines = []  # téléphones : fiabilité sur leur propre ligne (prospect_view)
    if s.place.website:
        lines.append(("Site", s.place.website, SURE))
    elif s.site and s.site.url:
        lines.append(("Site", s.site.url, LIKELY))
    elif s.site and s.site.probable:
        lines.append(("Site", s.site.probable, CHECK))
    company = s.company
    if company:
        level = SURE if s.registry_status == "sûr" else CHECK
        lines.append(("Entreprise", company.name, level))
        if company.leaders:
            lines.append(("Dirigeant", company.leaders[0], level))
    elif s.registry_status == "à confirmer":
        lines.append(("Entreprise", "pas trouvée avec certitude", CHECK))
    return lines
