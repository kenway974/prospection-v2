"""Refaire l'audit d'un site à la demande (C156) : la fiche demande, la tâche de fond lit le
site (gratuit), quelques sites à la fois ; la vitesse déjà mesurée par Google est gardée."""

import dataclasses
import logging
from datetime import datetime

from sqlalchemy import Engine

from prospection.application.prospect_card import UnknownProspect
from prospection.application.site_verdict import SiteChecker
from prospection.storage import reaudit_requests as store

BATCH = 5
logger = logging.getLogger(__name__)


def request_reaudit(engine: Engine, prospect_id: int, now: datetime) -> None:
    with engine.begin() as conn:
        if not store.request(conn, prospect_id, now):
            raise UnknownProspect(prospect_id)


def run_reaudits(engine: Engine, checker: SiteChecker, now: datetime) -> int:
    """Traite jusqu'à BATCH demandes ; sans lecteur de site (tests, outils), rien."""
    with engine.connect() as conn:
        waiting = store.pending(conn, BATCH)
    done = 0
    for prospect_id, place, keywords, old in waiting:
        try:
            report = checker(place, keywords)
        except Exception:  # site imprévu : demande abandonnée, l'ancien audit est gardé
            logger.exception("Site illisible pendant le nouvel audit")
            report = old
        else:
            if report is None:
                break
            report = dataclasses.replace(report, speed=old.speed if old else None)
        with engine.begin() as conn:
            store.done(conn, prospect_id, report)
        done += 1
    return done
