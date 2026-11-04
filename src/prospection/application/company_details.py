"""Compléter les entreprises des prospects (tâche de fond) : registre gratuit (labels,
établissements, dirigeants et chiffres s'ils manquent), puis registre national de l'INPI si
les identifiants sont saisis (objet social, activités, domaines) (C149, C150).

Quelques entreprises à la fois, en respectant les limites d'appels ; un service muet est
réessayé au prochain passage (rien n'est marqué fait).
"""

import logging
import time
from datetime import datetime

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.domain.company import Company, with_registry, with_rne
from prospection.domain.services import Service
from prospection.sources.company_details import company_by_siren
from prospection.sources.company_registry import RegistryRejected, RegistryUnavailable
from prospection.sources.rne import (
    RneExpired,
    RneRefused,
    RneUnavailable,
    rne_company,
    rne_login,
    split_key,
)
from prospection.storage.api_keys import load_key, record_test
from prospection.storage.company_details import pending_details, save_details
from prospection.storage.secret_box import SecretBox

BATCH = 10
PAUSE_SECONDS = 0.3  # registre : 7 appels par seconde ; INPI : sans rafale
REFUSED = "Identifiants refusés par l'INPI : vérifiez-les sur data.inpi.fr, puis « Tester »."
logger = logging.getLogger(__name__)


class _Rne:
    """Connexion INPI ouverte une fois par passage, rouverte si le jeton expire."""

    def __init__(self, client: httpx.Client, pair: tuple[str, str]) -> None:
        self.client, self.pair, self.token = client, pair, ""

    def details(self, company: Company) -> Company:
        for _ in range(2):
            self.token = self.token or rne_login(self.client, *self.pair)
            try:
                found = rne_company(self.client, self.token, company.siren)
            except RneExpired:
                self.token = ""
                continue
            if found is None:
                return with_rne(company, None, (), ())
            return with_rne(company, found.purpose, found.activities, found.domains)
        return with_rne(company, None, (), ())  # refusée deux fois : passer aux suivantes


def _complete(client: httpx.Client, rne: _Rne | None, company: Company) -> Company:
    if not company.detailed:
        try:
            company = with_registry(company, company_by_siren(client, company.siren))
        except RegistryRejected:
            company = with_registry(company, None)
    if rne and not company.rne_checked and company.diffusible:
        company = rne.details(company)
    return company


def detail_companies(
    engine: Engine, box: SecretBox, client: httpx.Client, now: datetime,
    pause: float = PAUSE_SECONDS,
) -> int:  # fmt: skip
    """Complète jusqu'à BATCH entreprises ; renvoie le nombre complété."""
    with engine.connect() as conn:
        stored = load_key(conn, Service.INPI)
    pair = split_key(read_key(engine, box, Service.INPI) or "")
    usable = pair and stored and stored.test_ok is not False  # refusés : plus d'essai
    rne = _Rne(client, pair) if pair and usable else None
    with engine.connect() as conn:
        pending = pending_details(conn, rne is not None, BATCH)
    done = 0
    for prospect_id, company in pending:
        try:
            completed = _complete(client, rne, company)
        except (RegistryUnavailable, RneUnavailable):
            break  # réessayé au prochain passage
        except RneRefused:
            logger.warning("Identifiants INPI refusés : registre national ignoré")
            if stored:
                with engine.begin() as conn:
                    record_test(conn, Service.INPI, stored.saved_at, now, False, REFUSED)
            break
        with engine.begin() as conn:
            save_details(conn, prospect_id, completed)
        done += 1
        time.sleep(pause)
    return done
