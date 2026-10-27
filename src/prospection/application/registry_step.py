"""Étape « registre » : une page d'entreprises récemment créées (C24 à C27, C44, C93).

Chaque entreprise est cherchée sur Google Maps (un appel, réservé dans le budget) pour son
numéro ; la fiche n'est retenue que si le rapprochement est sûr. Sinon l'entreprise est
gardée avec « numéro à chercher », et les critères habituels s'appliquent.
"""

import dataclasses
from datetime import date, datetime

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.application.registry_lookup import LookupContext, bare_place, look_up
from prospection.application.site_verdict import (
    SiteChecker,
    read_sites,
    skip_sites,
    with_site,
    worth_reading,
)
from prospection.application.step_flow import StepOutcome, finish, retry_later, skip
from prospection.domain.company import Company
from prospection.domain.criteria import Verdict, evaluate
from prospection.domain.google_cost import Pricing
from prospection.domain.place import Place
from prospection.domain.registry import (
    LOOKUPS_PER_TARGET,
    is_candidate,
    lookup_name,
    workforce_ok,
)
from prospection.domain.services import Service
from prospection.domain.site_report import SiteReport
from prospection.domain.trades import find_trade, load_trades
from prospection.sources.company_registry import RegistryUnavailable
from prospection.sources.sirene_search import (
    RecentQuery,
    SireneRefused,
    SireneRejected,
    recent_companies,
)
from prospection.storage.campaign_steps import Step, looked_up, record_page
from prospection.storage.campaigns import add_counts, add_event, load_campaign
from prospection.storage.exclusions import load_exclusions
from prospection.storage.prospects import insert_prospect
from prospection.storage.registry_status import known_sirens, set_company
from prospection.storage.secret_box import SecretBox

NO_INSEE_KEY = (
    "Clé Sirène absente : ajoutez-la dans Réglages → Clés API, ou choisissez la source Google Maps."
)
NOT_ON_MAPS = "Pas trouvée sur Google Maps : numéro à chercher"
BUSY = "Registre des entreprises trop sollicité"
NO_SIGN = "Entrepreneur individuel sans enseigne : site non cherché (nom d'une personne)"


def _query(step: Step) -> RecentQuery:
    r = step.registry or {}
    return RecentQuery(date.fromisoformat(r["since"]), date.fromisoformat(r["until"]),
                       r["area"], r["code"], tuple(r["naf_prefixes"]))  # fmt: skip


def _stopping(engine: Engine, campaign_id: int) -> bool:
    with engine.connect() as conn:
        return load_campaign(conn, campaign_id).status == "stopping"


def _site(
    sites: SiteChecker, company: Company, shown: Place, bare: bool, keyword: str,
    verdict: Verdict,
) -> SiteReport | None:  # fmt: skip
    """Site cherché à partir de l'enseigne ; jamais à partir du nom d'une personne (C47)."""
    if not worth_reading(verdict):
        return None
    name = lookup_name(company) if bare else shown.name
    if name is None:
        return SiteReport("aucun", problem=NO_SIGN)
    looked = dataclasses.replace(shown, name=name)
    return read_sites(sites, [looked], keyword)[shown.place_id]


def run_registry_step(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, campaign_id: int,
    step: Step, now: datetime, sites: SiteChecker = skip_sites,
) -> StepOutcome:  # fmt: skip
    insee_key = read_key(engine, box, Service.INSEE)
    if insee_key is None:
        return finish(engine, campaign_id, NO_INSEE_KEY, now)
    try:
        page = recent_companies(client, insee_key, _query(step), step.page_token or "*")
    except RegistryUnavailable:
        return retry_later(engine, campaign_id, step, now, BUSY)
    except SireneRefused as refused:
        return finish(engine, campaign_id, str(refused), now)
    except SireneRejected:
        return skip(engine, campaign_id, step, now, "Requête refusée par le registre")
    with engine.connect() as conn:
        campaign = load_campaign(conn, campaign_id)
        exclusions = load_exclusions(conn)
    criteria, trade = campaign.request.criteria, find_trade(step.keyword, load_trades())
    bare_criteria = dataclasses.replace(criteria, phone="any")  # le numéro reste à chercher
    google_key = read_key(engine, box, Service.GOOGLE)
    query = _query(step)
    with engine.connect() as conn:
        known = known_sirens(conn, campaign_id)
        paid = set(looked_up(conn, campaign_id))  # déjà cherchées (et payées) : jamais deux fois
    cap = campaign.request.target * LOOKUPS_PER_TARGET
    found = qualified = 0
    for company in page.companies:
        if campaign.qualified + qualified >= campaign.request.target or _stopping(
            engine, campaign_id
        ):
            break
        if company.siren in known or not is_candidate(company, query.since, query.naf_prefixes):
            continue
        if not workforce_ok(company.workforce, criteria.max_workforce):
            continue
        known.add(company.siren)
        place = None
        if google_key and company.siren not in paid and len(paid) < cap:
            paid.add(company.siren)
            ctx = LookupContext(engine, client, pricing, campaign_id, step, now, google_key)
            looked = look_up(ctx, company)
            if isinstance(looked, StepOutcome):
                return looked
            place = looked
        shown = place or bare_place(company)
        verdict = evaluate(shown, trade, criteria if place else bare_criteria, exclusions)
        if place is None:
            verdict = Verdict(verdict.qualified, verdict.reasons, (*verdict.to_check, NOT_ON_MAPS))
        report = _site(sites, company, shown, place is None, step.keyword, verdict)
        verdict = with_site(verdict, report, criteria)
        with engine.begin() as conn:  # enregistré au fil de l'eau : une reprise ne repaie rien
            if insert_prospect(conn, campaign_id, shown, step.keyword, verdict, now, report):
                set_company(conn, campaign_id, shown.place_id, company)
                ok = int(verdict.qualified)
                add_counts(conn, campaign_id, now, 1, 1 - ok, ok, 0)
                found, qualified = found + 1, qualified + ok
    with engine.begin() as conn:
        record_page(conn, step.id, page.next_cursor)
        message = f"{step.query} : {found} entreprises, {qualified} qualifiées"
        add_event(conn, campaign_id, now, "info", message)
    return StepOutcome(done=False)
