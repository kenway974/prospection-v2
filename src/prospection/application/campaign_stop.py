"""Faut-il arrêter la campagne, et pourquoi ? (C35, C36, C37)"""

from sqlalchemy import Engine

from prospection.domain.registry import REGISTRY
from prospection.domain.stop_reasons import exhausted, finished_with_skips, goal_reached
from prospection.storage.campaign_steps import next_step, skipped_steps
from prospection.storage.campaigns import load_campaign

STOPPED_BY_YOU = "Arrêtée à votre demande : les prospects trouvés sont gardés."


def stop_reason(engine: Engine, campaign_id: int) -> str | None:
    with engine.connect() as conn:
        c = load_campaign(conn, campaign_id)
        step = next_step(conn, campaign_id)
        skipped = skipped_steps(conn, campaign_id)
    if c.status == "stopping":
        return STOPPED_BY_YOU
    if c.qualified >= c.request.target:
        return goal_reached(c.qualified)
    if step is not None:
        return None
    if skipped:
        return finished_with_skips(skipped, c.qualified, c.request.target)
    return exhausted(c.qualified, c.request.target, c.request.sources == (REGISTRY,))
