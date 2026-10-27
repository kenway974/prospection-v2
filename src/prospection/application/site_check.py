"""Le site d'un établissement : lu depuis la fiche Google, ou retrouvé, puis audité (C46 à C52).

Lecture gratuite mais lente : appelée seulement pour les établissements qui passent déjà les
critères gratuits (C39). Les domaines devinés sont lus en parallèle (4 au plus).
"""

from concurrent.futures import ThreadPoolExecutor

import httpx

from prospection.domain.html_page import parse_page
from prospection.domain.place import Place, web_link
from prospection.domain.site_audit import audit
from prospection.domain.site_contacts import find_contacts
from prospection.domain.site_guess import STRONG, address_city, candidate_domains, confirmation
from prospection.domain.site_report import Origin, SiteReport
from prospection.domain.site_seo import local_seo
from prospection.sources.web_reader import ReadResult, read_page


def _report(
    result: ReadResult, origin: Origin, place: Place, keywords: tuple[str, ...], year: int
) -> SiteReport:
    if result.page is None:
        return SiteReport(origin, problem=result.problem)
    page = parse_page(result.page.html)
    return SiteReport(
        origin, result.page.url,
        audit=audit(page, result.page.url, result.page.seconds, year),
        seo=local_seo(page, keywords, address_city(place.address)),
        contacts=find_contacts(page, place.country or "FR"),
    )  # fmt: skip


def _guess(client: httpx.Client, place: Place, keywords: tuple[str, ...], year: int) -> SiteReport:
    domains = candidate_domains(place.name, place.country, keywords, address_city(place.address))
    if not domains:
        return SiteReport("aucun")
    with ThreadPoolExecutor(max_workers=len(domains)) as pool:
        results = list(pool.map(lambda d: read_page(client, f"https://{d}"), domains))
    probable = None
    for result in results:
        if result.page is None:
            continue
        page = parse_page(result.page.html)
        phones = find_contacts(page, place.country or "FR").phones
        level = confirmation(page.text, place.name, place.phone, place.address, phones)
        if level == STRONG:
            return _report(result, "retrouvé", place, keywords, year)
        probable = probable or (result.page.url if level else None)
    return SiteReport("aucun", probable=probable)


def check_site(
    client: httpx.Client, place: Place, keywords: tuple[str, ...], year: int
) -> SiteReport:
    """Rapport du site ; jamais d'exception pour un site absent ou en panne."""
    url = web_link(place.website)
    if url:
        return _report(read_page(client, url), "fiche Google", place, keywords, year)
    return _guess(client, place, keywords, year)
