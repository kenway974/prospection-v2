"""Refaire l'audit d'un site à la demande (C156) : la fiche demande, la tâche de fond lit le
site (gratuit), quelques sites à la fois ; la vitesse déjà mesurée par Google est gardée."""

import dataclasses
import logging
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Engine

from prospection.application.prospect_card import UnknownProspect
from prospection.application.prospect_selection import MAX_SELECTION as MAX
from prospection.application.site_verdict import SiteChecker
from prospection.storage import reaudit_requests as store

BATCH = 5
logger = logging.getLogger(__name__)


def request_reaudit(engine: Engine, prospect_id: int, now: datetime) -> None:
    with engine.begin() as conn:
        if not store.request(conn, prospect_id, now):
            raise UnknownProspect(prospect_id)


def request_reaudits(engine: Engine, prospect_ids: Sequence[int], now: datetime) -> int:
    """C185 : nouvel audit pour chaque prospect coché qui existe encore ; rend leur nombre."""
    with engine.begin() as conn:
        return sum(store.request(conn, i, now) for i in dict.fromkeys(prospect_ids[:MAX]))


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
            same_site = old is not None and old.url == report.url  # vitesse de ce site-là
            report = dataclasses.replace(report, speed=old.speed if same_site and old else None)
        with engine.begin() as conn:
            store.done(conn, prospect_id, report)
        done += 1
    return done
