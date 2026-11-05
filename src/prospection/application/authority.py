"""Autorité du domaine d'un site (C143) : Open PageRank, une requête gardée 30 jours.

Facultative : sans clé, ou si le service ne répond pas, rien n'est dit (None) et rien ne
bloque ; une panne n'est pas gardée, le domaine sera redemandé la fois suivante.
"""

from datetime import datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.domain.services import Service
from prospection.sources.open_pagerank import AuthorityUnavailable, page_rank
from prospection.storage.authority import load_authority, save_authority
from prospection.storage.secret_box import SecretBox

KEEP = timedelta(days=30)


def known_authority(engine: Engine, domain: str) -> float | None:
    """Valeur déjà connue, sans appel (affichage de la fiche)."""
    with engine.connect() as conn:
        known = load_authority(conn, domain)
    return known[0] if known else None


def domain_authority(
    engine: Engine, box: SecretBox, client: httpx.Client, domain: str, now: datetime
) -> float | None:
    with engine.connect() as conn:
        known = load_authority(conn, domain)
    if known and now - known[1] < KEEP:
        return known[0]
    key = read_key(engine, box, Service.OPENPAGERANK)
    if key is None:
        return known[0] if known else None
    try:
        rank = page_rank(client, key, domain)
    except AuthorityUnavailable:
        return known[0] if known else None
    with engine.begin() as conn:
        save_authority(conn, domain, rank, now)
    return rank
