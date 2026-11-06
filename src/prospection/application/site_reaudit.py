"""Réauditer les sites audités avant la nouvelle détection (C152) : formulaire sur la page
Contact, RGPD, contact. Lecture gratuite, quelques sites à la fois, par la tâche de fond ;
la vitesse déjà mesurée par Google est gardée."""

import dataclasses
import logging
from datetime import datetime

from sqlalchemy import Engine

from prospection.application.site_verdict import SiteChecker
from prospection.domain.site_form import UNKNOWN
from prospection.storage.site_reaudit import pending_reaudits, save_reaudit

BATCH = 5
logger = logging.getLogger(__name__)


def reaudit_sites(engine: Engine, checker: SiteChecker, now: datetime) -> int:
    """Réaudite jusqu'à BATCH sites ; renvoie le nombre fait. Sans lecteur de site (tests,
    outils) : rien."""
    with engine.connect() as conn:
        pending = pending_reaudits(conn, BATCH)
    done = 0
    for prospect_id, place, keywords, old in pending:
        try:
            report = checker(place, keywords)
        except Exception:  # site imprévu : « non vérifié », jamais retenté en boucle
            logger.exception("Site illisible pendant le nouvel audit")
            unsure = dataclasses.replace(old.audit, form_place=UNKNOWN) if old.audit else None
            report = dataclasses.replace(old, audit=unsure)
        if report is None:
            break
        with engine.begin() as conn:
            save_reaudit(conn, prospect_id, dataclasses.replace(report, speed=old.speed))
        done += 1
    return done
