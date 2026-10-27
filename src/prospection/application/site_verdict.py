"""Lire les sites des établissements retenus, puis appliquer les critères « site » (C28, C29,
C39, C46, C47).

La lecture est gratuite mais lente : seulement pour ce qui passe déjà les critères gratuits
(ou n'est écarté que faute de site sur la fiche : il est peut-être retrouvé), en parallèle.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from prospection.domain.criteria import Criteria, Verdict
from prospection.domain.place import Place
from prospection.domain.site_criteria import site_reasons
from prospection.domain.site_report import SiteReport

SiteChecker = Callable[[Place, tuple[str, ...]], SiteReport | None]
NO_SITE_REASON = "Sans site"
PROBABLE = "Site probable, à confirmer (homonyme possible)"
PARALLEL = 4
logger = logging.getLogger(__name__)


def skip_sites(place: Place, keywords: tuple[str, ...]) -> SiteReport | None:
    """Sites non lus (tests, outils) : aucun rapport, aucun critère « site » appliqué."""
    return None


def worth_reading(verdict: Verdict) -> bool:
    return verdict.qualified or verdict.reasons == (NO_SITE_REASON,)


def read_sites(
    checker: SiteChecker, places: list[Place], keyword: str
) -> dict[str, SiteReport | None]:
    if not places:
        return {}

    def read(place: Place) -> SiteReport | None:
        try:
            return checker(place, (keyword,))
        except Exception:  # un site imprévu ne doit pas arrêter la campagne (C41)
            logger.exception("Site illisible")
            return None

    with ThreadPoolExecutor(max_workers=min(PARALLEL, len(places))) as pool:
        reports = list(pool.map(read, places))
    return {p.place_id: r for p, r in zip(places, reports, strict=True)}


def with_site(verdict: Verdict, report: SiteReport | None, criteria: Criteria) -> Verdict:
    """Verdict complété par le site ; un site retrouvé lève « Sans site »."""
    if report is None:
        return verdict
    found = report.url is not None
    kept = [r for r in verdict.reasons if not (found and r == NO_SITE_REASON)]
    reasons = tuple(dict.fromkeys([*kept, *site_reasons(report, criteria)]))
    to_check = (*verdict.to_check, *([PROBABLE] if report.probable else []))
    return Verdict(not reasons, reasons, to_check)
