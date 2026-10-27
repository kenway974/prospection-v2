"""Briques communes aux étapes de campagne : fin, budget, nouvel essai (C07, C37, C41, C79)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Engine

from prospection.application.budget_settings import current_budget
from prospection.domain.google_cost import Pricing, billing_month, call_cost_cents, can_call
from prospection.domain.stop_reasons import budget_reached
from prospection.storage.campaign_steps import Step, count_attempt, skip_step
from prospection.storage.campaigns import add_counts, add_event, load_campaign, set_status
from prospection.storage.google_usage import add_call, lock_google, month_usage

RETRY_DELAYS = (timedelta(seconds=5), timedelta(seconds=30), timedelta(seconds=120))


@dataclass(frozen=True)
class StepOutcome:
    done: bool
    retry_at: datetime | None = None


def finish(engine: Engine, campaign_id: int, reason: str, now: datetime) -> StepOutcome:
    with engine.begin() as conn:
        set_status(conn, campaign_id, "done", now, reason)
        add_event(conn, campaign_id, now, "info", reason)
    return StepOutcome(done=True)


def reserve_call(engine: Engine, pricing: Pricing, campaign_id: int, now: datetime) -> bool:
    """Compte l'appel Google avant de le faire, si le plafond le permet (C07, C79)."""
    month, budget = billing_month(now), current_budget(engine)
    with engine.begin() as conn:
        lock_google(conn)
        calls, spent = month_usage(conn, month)
        if not can_call(pricing, calls, spent, budget):
            return False
        cost = call_cost_cents(pricing, calls)
        add_call(conn, month, cost)
        add_counts(conn, campaign_id, now, 0, 0, 0, cost)
    return True


def skip(engine: Engine, campaign_id: int, step: Step, now: datetime, problem: str) -> StepOutcome:
    with engine.begin() as conn:
        skip_step(conn, step.id)
        add_event(conn, campaign_id, now, "warning", f"{problem} : page ignorée")
    return StepOutcome(done=False)


def retry_later(
    engine: Engine, campaign_id: int, step: Step, now: datetime, problem: str
) -> StepOutcome:
    """Nouvel essai après 5 s, 30 s puis 2 min ; ensuite la page est ignorée (C41)."""
    with engine.begin() as conn:
        attempts = count_attempt(conn, step.id)
    if attempts > len(RETRY_DELAYS):
        return skip(engine, campaign_id, step, now, problem)
    with engine.begin() as conn:
        add_event(conn, campaign_id, now, "warning", f"{problem} : nouvel essai bientôt")
    return StepOutcome(done=False, retry_at=now + RETRY_DELAYS[attempts - 1])


def budget_stop(engine: Engine, campaign_id: int, now: datetime) -> StepOutcome:
    """Plafond ou quota gratuit atteint : la campagne s'arrête et garde ce qu'elle a (C37)."""
    with engine.connect() as conn:
        c = load_campaign(conn, campaign_id)
    reason = budget_reached(current_budget(engine), c.qualified, c.request.target)
    return finish(engine, campaign_id, reason, now)
