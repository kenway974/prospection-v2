"""Enregistrer une page de résultats Google (C38, C39, C41, C13)."""

import logging
from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.criteria import Verdict, evaluate
from prospection.domain.geo import distance_m
from prospection.domain.place import Place
from prospection.domain.trades import find_trade, load_trades
from prospection.sources.google_search import SearchPage
from prospection.storage.campaign_steps import Step, record_page
from prospection.storage.campaigns import add_counts, add_event, load_campaign
from prospection.storage.exclusions import load_exclusions
from prospection.storage.prospects import insert_prospect

logger = logging.getLogger(__name__)


def _outside_radius(place: Place, step: Step) -> str | None:
    if not (step.restrict_to_bias and step.bias and place.lat is not None and place.lon):
        return None
    km = distance_m(step.bias.lat, step.bias.lon, place.lat, place.lon) / 1000
    return f"Hors zone ({km:.0f} km)" if km * 1000 > step.bias.radius_m else None


def save_page(
    engine: Engine, campaign_id: int, step: Step, page: SearchPage, now: datetime
) -> None:
    """Évalue chaque établissement ; une erreur sur l'un n'arrête pas la campagne (C41)."""
    trade = find_trade(step.keyword, load_trades())
    found = excluded = qualified = 0
    with engine.begin() as conn:
        criteria = load_campaign(conn, campaign_id).request.criteria
        exclusions = load_exclusions(conn)
        for place in page.places:
            try:
                verdict = evaluate(place, trade, criteria, exclusions)
                outside = _outside_radius(place, step)
                if outside:
                    verdict = Verdict(False, (*verdict.reasons, outside), verdict.to_check)
                with conn.begin_nested():  # une erreur de base n'annule que cet établissement
                    new = insert_prospect(conn, campaign_id, place, step.keyword, verdict, now)
                if new:
                    found += 1
                    qualified += verdict.qualified
                    excluded += not verdict.qualified
            except Exception:  # un établissement fautif ne doit pas tout arrêter
                logger.exception("Établissement ignoré")
                add_event(conn, campaign_id, now, "warning", "Un établissement n'a pas pu être lu")
        record_page(conn, step.id, page.next_token)
        add_counts(conn, campaign_id, now, found, excluded, qualified, 0)
        number = step.page_number + 1
        message = f"{step.query} · page {number} : {found} nouveaux, {qualified} qualifiés"
        add_event(conn, campaign_id, now, "info", message)
        if page.skipped:
            plural = "s" if page.skipped > 1 else ""
            message = f"{page.skipped} établissement{plural} illisible{plural} ignoré{plural}"
            add_event(conn, campaign_id, now, "warning", message)
