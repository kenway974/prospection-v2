"""Rapprocher les prospects trouvés sur Google du registre des entreprises (C44, C45, C93).

Gratuit (API Recherche d'entreprises) ; fait par la tâche de fond, quelques prospects à la
fois, en respectant la limite d'appels du service. Un service muet est réessayé plus tard.
"""

import time
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.domain.company import match_company, postal_code
from prospection.domain.territories import FRENCH_TERRITORIES
from prospection.sources.company_registry import (
    RegistryRejected,
    RegistryUnavailable,
    search_companies,
)
from prospection.storage.registry_status import (
    NOT_FRENCH,
    SURE,
    TO_CONFIRM,
    pending_prospects,
    save_match,
)

BATCH = 20
PAUSE_SECONDS = 0.15  # le service accepte 7 appels par seconde
MIN_NAME = 3  # le service refuse une recherche plus courte


def enrich_new_prospects(
    engine: Engine, client: httpx.Client, now: datetime, pause: float = PAUSE_SECONDS
) -> int:
    """Rapproche jusqu'à BATCH prospects ; renvoie le nombre traité."""
    with engine.connect() as conn:
        pending = pending_prospects(conn, BATCH)
    done = 0
    for prospect in pending:
        if prospect.country not in FRENCH_TERRITORIES:
            with engine.begin() as conn:
                save_match(conn, prospect.id, None, NOT_FRENCH)
            done += 1
            continue
        postal = postal_code(prospect.address)
        try:
            too_short = len(prospect.name.strip()) < MIN_NAME
            candidates = [] if too_short else search_companies(client, prospect.name, postal)
        except RegistryUnavailable:
            break  # on réessaiera au prochain passage
        except RegistryRejected:  # cette recherche-là ne passera jamais : à confirmer à la main
            candidates = []
        match = match_company(prospect.name, postal, candidates)
        with engine.begin() as conn:
            save_match(conn, prospect.id, match.company, SURE if match.sure else TO_CONFIRM)
        done += 1
        time.sleep(pause)
    return done
