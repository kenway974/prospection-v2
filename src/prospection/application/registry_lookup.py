"""Chercher une entreprise du registre sur Google Maps, sans jamais payer deux fois (C24, C40)."""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.step_flow import (
    StepOutcome,
    budget_stop,
    finish,
    reserve_call,
    retry_later,
)
from prospection.domain.company import Company, match_place
from prospection.domain.google_cost import Pricing
from prospection.domain.place import Place
from prospection.domain.registry import lookup_name
from prospection.sources.google_search import (
    GoogleBusy,
    GoogleRefused,
    GoogleRejectedPage,
    search_page,
)
from prospection.storage.campaign_steps import Step, mark_looked_up

BUSY = "Google trop sollicité"
logger = logging.getLogger(__name__)


@dataclass
class LookupContext:
    engine: Engine
    client: httpx.Client
    pricing: Pricing
    campaign_id: int
    step: Step
    now: datetime
    key: str


def bare_place(company: Company) -> Place:
    """Entreprise absente de Google Maps : seulement ce que dit le registre."""
    address = " ".join(p for p in (company.postal_code, company.city) if p)
    return Place(f"siren:{company.siren}", company.name, address, None, None, (), None, None,
                 None, None, None, 0, (), None, 0, "inconnu", "FR")  # fmt: skip


def look_up(ctx: LookupContext, company: Company) -> Place | StepOutcome | None:
    """Fiche Google de l'entreprise (appel réservé et noté d'abord), ou l'issue de l'étape."""
    name = lookup_name(company)
    if name is None:
        return None
    if not reserve_call(ctx.engine, ctx.pricing, ctx.campaign_id, ctx.now):
        return budget_stop(ctx.engine, ctx.campaign_id, ctx.now)
    with ctx.engine.begin() as conn:
        mark_looked_up(conn, ctx.step.id, company.siren)
    try:
        result = search_page(ctx.client, ctx.key, f"{name} {company.city or ''}", None, None, "FR")
    except GoogleRejectedPage:
        return None  # cette requête-là est refusée : on garde l'entreprise, numéro à chercher
    except GoogleBusy:
        return retry_later(ctx.engine, ctx.campaign_id, ctx.step, ctx.now, BUSY)
    except GoogleRefused as refused:
        return finish(ctx.engine, ctx.campaign_id, str(refused), ctx.now)
    except Exception:  # réponse imprévue : nouveaux essais plafonnés, jamais sans fin
        logger.exception("Réponse Google illisible (registre, campagne %s)", ctx.campaign_id)
        return retry_later(ctx.engine, ctx.campaign_id, ctx.step, ctx.now, BUSY)
    return match_place(company, result.places)
