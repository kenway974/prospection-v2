"""Une étape de campagne = une page Google (C34 à C41, C07, C79).

Rejouée par la tâche de fond jusqu'à `done`. Chaque appel Google est réservé
(compté) avant d'être fait ; les résultats et la page suivante sont enregistrés
ensemble : une reprise après coupure ne compte rien deux fois (C40).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.application.budget_settings import current_budget
from prospection.application.page_results import save_page
from prospection.domain.google_cost import Pricing, billing_month, call_cost_cents, can_call
from prospection.domain.services import Service
from prospection.domain.stop_reasons import budget_reached, exhausted, goal_reached
from prospection.sources.google_search import (
    GoogleBusy,
    GoogleRefused,
    GoogleRejectedPage,
    search_page,
)
from prospection.storage.campaign_steps import Step, count_attempt, next_step, skip_step
from prospection.storage.campaigns import add_counts, add_event, load_campaign, set_status
from prospection.storage.google_usage import add_call, lock_google, month_usage
from prospection.storage.secret_box import SecretBox

RETRY_DELAYS = (timedelta(seconds=5), timedelta(seconds=30), timedelta(seconds=120))
BUSY = "Google trop sollicité"
UNSAVED = "Page de résultats impossible à enregistrer"
NO_KEY = "Clé Google absente ou illisible : ajoutez-la dans Réglages → Clés API."
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StepOutcome:
    done: bool
    retry_at: datetime | None = None


def _finish(engine: Engine, campaign_id: int, reason: str, now: datetime) -> StepOutcome:
    with engine.begin() as conn:
        set_status(conn, campaign_id, "done", now, reason)
        add_event(conn, campaign_id, now, "info", reason)
    return StepOutcome(done=True)


def _reserve_call(
    engine: Engine, pricing: Pricing, campaign_id: int, month: str, now: datetime
) -> bool:
    """Compte l'appel avant de le faire, si le plafond le permet (C07, C79)."""
    budget = current_budget(engine)
    with engine.begin() as conn:
        lock_google(conn)
        calls, spent = month_usage(conn, month)
        if not can_call(pricing, calls, spent, budget):
            return False
        cost = call_cost_cents(pricing, calls)
        add_call(conn, month, cost)
        add_counts(conn, campaign_id, now, 0, 0, 0, cost)
    return True


def _skip(engine: Engine, campaign_id: int, step: Step, now: datetime, problem: str) -> StepOutcome:
    with engine.begin() as conn:
        skip_step(conn, step.id)
        add_event(conn, campaign_id, now, "warning", f"{problem} : page ignorée")
    return StepOutcome(done=False)


def _retry_later(
    engine: Engine, campaign_id: int, step: Step, now: datetime, problem: str
) -> StepOutcome:
    """Nouvel essai après 5 s, 30 s puis 2 min ; ensuite la page est ignorée (C41)."""
    with engine.begin() as conn:
        attempts = count_attempt(conn, step.id)
    if attempts > len(RETRY_DELAYS):
        return _skip(engine, campaign_id, step, now, problem)
    with engine.begin() as conn:
        add_event(conn, campaign_id, now, "warning", f"{problem} : nouvel essai bientôt")
    return StepOutcome(done=False, retry_at=now + RETRY_DELAYS[attempts - 1])


def _stop_reason(engine: Engine, campaign_id: int) -> str | None:
    with engine.connect() as conn:
        c = load_campaign(conn, campaign_id)
        step = next_step(conn, campaign_id)
    if c.status == "stopping":
        return "Arrêtée à votre demande : les prospects trouvés sont gardés."
    if c.qualified >= c.request.target:
        return goal_reached(c.qualified)
    return exhausted(c.qualified, c.request.target) if step is None else None


def run_step(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, campaign_id: int,
    now: datetime,
) -> StepOutcome:  # fmt: skip
    with engine.connect() as conn:
        if load_campaign(conn, campaign_id).status == "done":
            return StepOutcome(done=True)
    reason = _stop_reason(engine, campaign_id)
    if reason:
        return _finish(engine, campaign_id, reason, now)
    key = read_key(engine, box, Service.GOOGLE)
    if key is None:
        return _finish(engine, campaign_id, NO_KEY, now)
    with engine.connect() as conn:
        step = next_step(conn, campaign_id)
    if step is None:  # toutes les pages lues entre-temps
        return run_step(engine, box, client, pricing, campaign_id, now)
    month = billing_month(now)
    if not _reserve_call(engine, pricing, campaign_id, month, now):
        with engine.connect() as conn:
            c = load_campaign(conn, campaign_id)
        reason = budget_reached(current_budget(engine), c.qualified, c.request.target)
        return _finish(engine, campaign_id, reason, now)
    try:
        page = search_page(client, key, step.query, step.bias, step.page_token, step.country)
    except GoogleBusy:
        return _retry_later(engine, campaign_id, step, now, BUSY)
    except GoogleRejectedPage:
        return _skip(engine, campaign_id, step, now, "Requête refusée par Google")
    except GoogleRefused as refused:
        return _finish(engine, campaign_id, str(refused), now)
    except Exception:  # réponse imprévue : l'appel réservé ne doit pas être refait sans fin
        logger.exception("Réponse Google illisible pour la campagne %s", campaign_id)
        return _retry_later(engine, campaign_id, step, now, BUSY)
    try:
        save_page(engine, campaign_id, step, page, now)
    except Exception:  # sans plafond d'essais, la même page serait rappelée (et payée) sans fin
        logger.exception("Page de la campagne %s non enregistrée", campaign_id)
        return _retry_later(engine, campaign_id, step, now, UNSAVED)
    reason = _stop_reason(engine, campaign_id)
    return _finish(engine, campaign_id, reason, now) if reason else StepOutcome(done=False)
