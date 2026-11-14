"""Le site d'un établissement : lu depuis la fiche Google, ou retrouvé, puis audité (C46 à C52).

Lecture gratuite mais lente : appelée seulement pour les établissements qui passent déjà les
critères gratuits (C39). Les domaines devinés sont lus en parallèle (4 au plus).
"""

from concurrent.futures import ThreadPoolExecutor
from time import monotonic

import httpx

from prospection.application.site_emails import Reader, site_contacts
from prospection.application.site_network import Shared, network_of
from prospection.domain.html_page import Page, parse_page
from prospection.domain.place import Place, web_link
from prospection.domain.site_audit import audit, is_placeholder
from prospection.domain.site_contacts import find_contacts
from prospection.domain.site_form import contact_links, has_form
from prospection.domain.site_guess import STRONG, address_city, candidate_domains, confirmation
from prospection.domain.site_js import is_js_app
from prospection.domain.site_owner import speaks_of
from prospection.domain.site_report import Origin, SiteReport
from prospection.domain.site_seo import local_seo
from prospection.sources.web_reader import UNREACHABLE, ReadResult, read_page

CONTACT_SECONDS = 8.0  # budget commun des pages Contact d'un site (C138)
BROWSER_SECONDS = 20.0  # un vrai navigateur exécute le JavaScript : plus lent (C166)
MIN_READ_SECONDS = 1.0
PLACEHOLDER = "Page « en construction » de l'hébergeur : aucun vrai site en ligne"


def _contact_pages(read: Reader, home: Page, url: str, budget: float) -> tuple[Page, ...]:
    """Pages Contact du même site, lues seulement si l'accueil n'a pas de formulaire (C138)."""
    if has_form(home):
        return ()
    pages: list[Page] = []
    start = monotonic()
    for link in contact_links(home, url):
        left = budget - (monotonic() - start)
        if left < MIN_READ_SECONDS:  # un seul budget pour toutes les pages Contact
            break
        result = read(link, left)
        if result.page is None:
            continue
        pages.append(parse_page(result.page.html, result.page.truncated))
        if has_form(pages[-1]):
            break
    return tuple(pages)


def _plain(client: httpx.Client) -> Reader:
    return lambda url, seconds: read_page(client, url, seconds=seconds)


def _rendered(page: Page, url: str, browser: Reader | None) -> Page | None:
    """C166 : coquille JavaScript relue par un vrai navigateur ; None si rien de mieux."""
    if browser is None or not is_js_app(page):
        return None
    result = browser(url, BROWSER_SECONDS)
    return parse_page(result.page.html, result.page.truncated) if result.page else None


def _report(
    client: httpx.Client, read_url: tuple[ReadResult, bool], origin: Origin, place: Place,
    keywords: tuple[str, ...], year: int, browser: Reader | None = None,
) -> SiteReport:  # fmt: skip
    result, https_failed = read_url
    if result.page is None:
        return SiteReport(origin, problem=result.problem)
    read = result.page
    page = parse_page(read.html, read.truncated)
    if is_placeholder(page):  # domaine acheté, aucun site en ligne : un prospect sans site
        return SiteReport(origin, problem=PLACEHOLDER, parked=True)
    rendered = _rendered(page, read.url, browser)
    reader: Reader = browser if rendered is not None and browser is not None else _plain(client)
    budget = BROWSER_SECONDS if reader is browser else CONTACT_SECONDS
    page = rendered or page
    others = _contact_pages(reader, page, read.url, budget)
    country = place.country or "FR"
    contacts = site_contacts(reader, page, others, read.url, country)  # C188
    blind = rendered is None and is_js_app(page)  # coquille non lue : on ne juge pas (C152)
    unsure = origin == "fiche Google" and not blind  # un site retrouvé est déjà confirmé
    return SiteReport(
        origin, read.url,
        audit=audit(page, read.url, read.seconds, year, read.powered_by, others, keywords,
                    https_failed, country),
        seo=local_seo(page, keywords, address_city(place.address)), contacts=contacts,
        unconfirmed=unsure and not speaks_of(place, read.url, [page, *others], contacts.phones),
    )  # fmt: skip


def _read_url(client: httpx.Client, url: str) -> tuple[ReadResult, bool]:
    """L'adresse donnée ; si https ne répond pas (certificat cassé…), la même en http : les
    sites faibles, la cible, n'ont souvent pas de HTTPS. Vrai si https a échoué (C141)."""
    result = read_page(client, url)
    if result.page is None and result.problem == UNREACHABLE and url.startswith("https://"):
        fallback = read_page(client, "http://" + url.removeprefix("https://"))
        return fallback, fallback.page is not None
    return result, False


def _read_domain(client: httpx.Client, domain: str) -> tuple[ReadResult, bool]:
    return _read_url(client, f"https://{domain}")


def _guess(
    client: httpx.Client, place: Place, keywords: tuple[str, ...], year: int,
    browser: Reader | None,
) -> SiteReport:  # fmt: skip
    domains = candidate_domains(place.name, place.country, keywords, address_city(place.address))
    if not domains:
        return SiteReport("aucun")
    with ThreadPoolExecutor(max_workers=len(domains)) as pool:
        results = list(pool.map(lambda d: _read_domain(client, d), domains))
    probable = None
    for read_url in results:
        result = read_url[0]
        if result.page is None:
            continue
        page = parse_page(result.page.html)
        phones = find_contacts(page, place.country or "FR").phones
        level = confirmation(page.text, place.name, place.phone, place.address, phones)
        if level == STRONG:
            return _report(client, read_url, "retrouvé", place, keywords, year, browser)
        probable = probable or (result.page.url if level else None)
    return SiteReport("aucun", probable=probable)


def check_site(
    client: httpx.Client, place: Place, keywords: tuple[str, ...], year: int,
    browser: Reader | None = None, shared: Shared | None = None,
) -> SiteReport:  # fmt: skip
    """Rapport du site ; jamais d'exception pour un site absent ou en panne. `browser` : lecture
    par un vrai navigateur, pour les sites affichés seulement par JavaScript (C166) ; `shared` :
    autres entreprises sur le même domaine (C174)."""
    url = web_link(place.website)
    network = network_of(url, place.name, shared) if url else None
    if url and network is None:
        read_url = _read_url(client, url)
        return _report(client, read_url, "fiche Google", place, keywords, year, browser)
    found = _guess(client, place, keywords, year, browser)
    if network is None or found.url:
        return found
    problem = f"La fiche Google renvoie vers {network} : pas de vrai site"  # C154
    return SiteReport("aucun", probable=found.probable, problem=problem, parked=True)
