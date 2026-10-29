"""Score d'opportunité sur 100, plus haut = meilleure opportunité, avec le détail (C57).

Repris de prospection-bot (services/opportunity.py, version 530ba12), adapté aux données de
la v2 : une entreprise récemment créée compte en plus ; chaque point « à vérifier » baisse le
score. Chaque ligne du détail est affichée telle quelle.
"""

from prospection.domain.page_speed import is_slow
from prospection.domain.signals import Signals, months

NO_SITE, WEAK_FACTOR, NO_FORM, FOUND_SITE, SITE_DOWN = 55, 0.5, 15, 5, 40
FEW_REVIEWS = ((10, 20, "Très peu d'avis Google"), (30, 10, "Peu d'avis Google"))
MANY_REVIEWS, MANY_POINTS = 100, -10
SOLID, SOLID_REVIEWS, SOLID_RATING, SOLID_SITE = -40, 50, 4.5, 80
NO_PHONE, YOUNG, YOUNG_DAYS, FLAG = -25, 10, 365, -5
SLOW_SITE = 15
CHAIN, CHAIN_FLAG = -20, "Nom proche de l'enseigne"


def _site(s: Signals) -> list[tuple[str, int]]:
    audit = s.audit
    if not s.has_site:
        return [("Aucun site (ni sur la fiche Google, ni retrouvé)", NO_SITE)]
    if s.site_down:
        return [("Site injoignable ou illisible", SITE_DOWN)]
    lines = []
    if audit and (weak := round((100 - audit.score) * WEAK_FACTOR)):
        lines.append((f"Site à améliorer (qualité {audit.score}/100)", weak))
    if audit and not audit.contact_form:
        lines.append(("Pas de formulaire de contact", NO_FORM))
    if s.site and is_slow(s.site.speed) and s.site.speed:
        lines.append((f"Site lent sur mobile (Google : {s.site.speed.score}/100)", SLOW_SITE))
    if s.site and s.site.origin == "retrouvé":
        lines.append(("Site absent de la fiche Google", FOUND_SITE))
    return lines


def _reviews(s: Signals) -> list[tuple[str, int]]:
    count = s.place.review_count
    for limit, points, label in FEW_REVIEWS:
        if count < limit:
            return [(f"{label} ({count})", points)]
    return [(f"Beaucoup d'avis Google ({count})", MANY_POINTS)] if count >= MANY_REVIEWS else []


def _solid(s: Signals) -> bool:
    audit = s.audit
    return bool(audit and audit.score >= SOLID_SITE and s.place.review_count >= SOLID_REVIEWS
                and (s.place.rating or 0) >= SOLID_RATING)  # fmt: skip


def opportunity(s: Signals) -> tuple[int, list[tuple[str, int]]]:
    details = [*_site(s), *_reviews(s)]
    if _solid(s):
        details.append(("Présence déjà solide (bon site, beaucoup d'avis bien notés)", SOLID))
    if s.age_days is not None and s.age_days <= YOUNG_DAYS:
        details.append((f"Entreprise créée il y a {months(s.age_days)}", YOUNG))
    if not s.place.phone:
        details.append(("Pas de téléphone (fiche à compléter)", NO_PHONE))
    for flag in s.flags:
        details.append((f"À vérifier : {flag}", CHAIN if flag.startswith(CHAIN_FLAG) else FLAG))
    return max(0, min(100, sum(points for _, points in details))), details
