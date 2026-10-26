"""Une étape de campagne = une page Google (C34 à C41, C07, C79).

Rejouée par la tâche de fond jusqu'à `done`. Chaque appel Google est réservé
(compté) avant d'être fait ; les résultats et la page suivante sont enregistrés
ensemble : une reprise après coupure ne compte rien deux fois (C40).
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.application.campaign_stop import stop_reason
from prospection.application.page_results import save_page
from prospection.application.registry_step import run_registry_step
from prospection.application.step_flow import (
    StepOutcome,
    budget_stop,
    finish,
    reserve_call,
    retry_later,
    skip,
)
from prospection.domain.google_cost import Pricing
from prospection.domain.registry import REGISTRY
from prospection.domain.services import Service
from prospection.sources.google_search import (
    GoogleBusy,
    GoogleRefused,
    GoogleRejectedPage,
    search_page,
)
from prospection.storage.campaign_steps import next_step
from prospection.storage.campaigns import load_campaign
from prospection.storage.secret_box import SecretBox

BUSY = "Google trop sollicité"
UNSAVED = "Page de résultats impossible à enregistrer"
NO_KEY = "Clé Google absente ou illisible : ajoutez-la dans Réglages → Clés API."
logger = logging.getLogger(__name__)


def run_step(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, campaign_id: int,
    now: datetime,
) -> StepOutcome:  # fmt: skip
    with engine.connect() as conn:
        if load_campaign(conn, campaign_id).status == "done":
            return StepOutcome(done=True)
    reason = stop_reason(engine, campaign_id)
    if reason:
        return finish(engine, campaign_id, reason, now)
    with engine.connect() as conn:
        step = next_step(conn, campaign_id)
    if step is None:  # toutes les pages lues entre-temps
        return run_step(engine, box, client, pricing, campaign_id, now)
    if step.kind == REGISTRY:
        return run_registry_step(engine, box, client, pricing, campaign_id, step, now)
    key = read_key(engine, box, Service.GOOGLE)
    if key is None:
        return finish(engine, campaign_id, NO_KEY, now)
    if not reserve_call(engine, pricing, campaign_id, now):
        return budget_stop(engine, campaign_id, now)
    try:
        page = search_page(client, key, step.query, step.bias, step.page_token, step.country)
    except GoogleBusy:
        return retry_later(engine, campaign_id, step, now, BUSY)
    except GoogleRejectedPage:
        return skip(engine, campaign_id, step, now, "Requête refusée par Google")
    except GoogleRefused as refused:
        return finish(engine, campaign_id, str(refused), now)
    except Exception:  # réponse imprévue : l'appel réservé ne doit pas être refait sans fin
        logger.exception("Réponse Google illisible pour la campagne %s", campaign_id)
        return retry_later(engine, campaign_id, step, now, BUSY)
    try:
        save_page(engine, campaign_id, step, page, now)
    except Exception:  # sans plafond d'essais, la même page serait rappelée (et payée) sans fin
        logger.exception("Page de la campagne %s non enregistrée", campaign_id)
        return retry_later(engine, campaign_id, step, now, UNSAVED)
    reason = stop_reason(engine, campaign_id)
    return finish(engine, campaign_id, reason, now) if reason else StepOutcome(done=False)
