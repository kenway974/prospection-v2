"""RGPD : purge automatique (C94) et suppression d'une entreprise sur demande (C95)."""

import logging
from datetime import datetime

from sqlalchemy import Engine

from prospection.domain.privacy import purge_cutoff
from prospection.storage import privacy as store
from prospection.storage.app_settings import load_app_settings, save_purge_months
from prospection.storage.prospect_list import load_prospect

logger = logging.getLogger(__name__)
MONTHS = range(1, 25)


class InvalidPurge(ValueError):
    """Durée hors limites ; le message dit quoi faire."""


def purge_months(engine: Engine) -> int:
    with engine.connect() as conn:
        return load_app_settings(conn).purge_months


def change_purge_months(engine: Engine, months: str) -> None:
    clean = months.strip()
    value = int(clean) if clean.isascii() and clean.isdigit() else 0
    if value not in MONTHS:
        raise InvalidPurge("Choisissez entre 1 et 24 mois.")
    with engine.begin() as conn:
        save_purge_months(conn, value)


def purge(engine: Engine, now: datetime) -> int:
    """Supprime les non retenus inactifs depuis la durée réglée ; renvoie combien."""
    with engine.begin() as conn:
        cutoff = purge_cutoff(now, load_app_settings(conn).purge_months)
        count = store.purge_inactive(conn, cutoff)
    if count:
        logger.info("Purge RGPD : %s prospects supprimés", count)
    return count


def erase_company(engine: Engine, prospect_id: int, keep_blacklist: bool = False) -> int:
    """Toutes ses données, dans toutes les campagnes ; elle ne sera plus jamais reprise."""
    with engine.begin() as conn:
        return store.erase_company(conn, prospect_id, keep_blacklist)


def company_name(engine: Engine, prospect_id: int) -> str | None:
    """Nom affiché avant de confirmer la suppression ; None si inconnu."""
    with engine.connect() as conn:
        prospect = load_prospect(conn, prospect_id)
    return None if prospect is None else str(prospect.data.get("name") or "Cette entreprise")
