"""Étape « registre » : une page d'entreprises récemment créées (C24 à C27, C44, C93).

Chaque entreprise est cherchée sur Google Maps (un appel, réservé dans le budget) pour son
numéro ; la fiche n'est retenue que si le rapprochement est sûr. Sinon l'entreprise est
gardée avec « numéro à chercher », et les critères habituels s'appliquent.
"""

import logging
from datetime import date, datetime

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.application.step_flow import (
    StepOutcome,
    budget_stop,
    finish,
    reserve_call,
    retry_later,
)
from prospection.domain.company import Company, match_place
from prospection.domain.criteria import Verdict, evaluate
from prospection.domain.google_cost import Pricing
from prospection.domain.place import Place
from prospection.domain.registry import workforce_ok
from prospection.domain.services import Service
from prospection.domain.trades import find_trade, load_trades
from prospection.sources.company_registry import RegistryUnavailable
from prospection.sources.google_search import (
    GoogleBusy,
    GoogleRefused,
    GoogleRejectedPage,
    search_page,
)
from prospection.sources.sirene_search import RecentQuery, SireneRefused, recent_companies
from prospection.storage.campaign_steps import Step, record_page
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
logger = logging.getLogger(__name__)


def _query(step: Step) -> RecentQuery:
    r = step.registry or {}
    return RecentQuery(date.fromisoformat(r["since"]), date.fromisoformat(r["until"]),
                       r["area"], r["code"], tuple(r["naf_prefixes"]))  # fmt: skip


def _bare_place(company: Company) -> Place:
    """Entreprise absente de Google Maps : seulement ce que dit le registre."""
    address = " ".join(p for p in (company.postal_code, company.city) if p)
    return Place(f"siren:{company.siren}", company.name, address, None, None, (), None, None,
                 None, None, None, 0, (), None, 0, "inconnu", "FR")  # fmt: skip


def _known(engine: Engine, campaign_id: int) -> set[str]:
    with engine.connect() as conn:
        return known_sirens(conn, campaign_id)


def _look_up(
    engine: Engine, client: httpx.Client, pricing: Pricing, campaign_id: int, step: Step,
    now: datetime, key: str, company: Company,
) -> Place | StepOutcome | None:  # fmt: skip
    """Fiche Google de l'entreprise (appel réservé d'abord), ou l'issue de l'étape."""
    if not reserve_call(engine, pricing, campaign_id, now):
        return budget_stop(engine, campaign_id, now)
    try:
        result = search_page(client, key, f"{company.name} {company.city or ''}", None, None, "FR")
    except GoogleRejectedPage:
        return None  # cette requête-là est refusée : on garde l'entreprise, numéro à chercher
    except GoogleBusy:
        return retry_later(engine, campaign_id, step, now, "Google trop sollicité")
    except GoogleRefused as refused:
        return finish(engine, campaign_id, str(refused), now)
    except Exception:  # réponse imprévue : nouveaux essais plafonnés, jamais sans fin
        logger.exception("Réponse Google illisible (registre, campagne %s)", campaign_id)
        return retry_later(engine, campaign_id, step, now, "Google trop sollicité")
    return match_place(company, result.places)


def run_registry_step(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, campaign_id: int,
    step: Step, now: datetime,
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
    with engine.connect() as conn:
        campaign = load_campaign(conn, campaign_id)
        exclusions = load_exclusions(conn)
    criteria, trade = campaign.request.criteria, find_trade(step.keyword, load_trades())
    google_key = read_key(engine, box, Service.GOOGLE)
    found = qualified = 0
    known = _known(engine, campaign_id)
    for company in page.companies:
        if campaign.qualified + qualified >= campaign.request.target:
            break
        if company.siren in known or not workforce_ok(company.workforce, criteria.max_workforce):
            continue
        place = None
        if google_key:
            looked = _look_up(engine, client, pricing, campaign_id, step, now, google_key, company)
            if isinstance(looked, StepOutcome):
                return looked
            place = looked
        shown = place or _bare_place(company)
        verdict = evaluate(shown, trade, criteria, exclusions)
        if place is None:
            verdict = Verdict(verdict.qualified, verdict.reasons, (*verdict.to_check, NOT_ON_MAPS))
        with engine.begin() as conn:  # enregistré au fil de l'eau : une reprise ne repaie rien
            if insert_prospect(conn, campaign_id, shown, step.keyword, verdict, now):
                set_company(conn, campaign_id, shown.place_id, company)
                ok = int(verdict.qualified)
                add_counts(conn, campaign_id, now, 1, 1 - ok, ok, 0)
                found, qualified = found + 1, qualified + ok
    with engine.begin() as conn:
        record_page(conn, step.id, page.next_cursor)
        message = f"{step.query} : {found} entreprises, {qualified} qualifiées"
        add_event(conn, campaign_id, now, "info", message)
    return StepOutcome(done=False)
