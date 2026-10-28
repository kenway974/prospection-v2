"""Vérification hebdomadaire des vraies API (C99), hors CI, par la tâche de fond : clés
encore acceptées et réponses toujours au format attendu ; sinon, une alerte."""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import read_key
from prospection.application.key_tests import run_key_test
from prospection.application.step_flow import reserve_call
from prospection.domain.google_cost import Pricing
from prospection.domain.services import Service
from prospection.sources.company_registry import search_companies
from prospection.sources.google_search import search_page
from prospection.storage.alerts import add_alert
from prospection.storage.api_keys import load_key
from prospection.storage.maintenance import claim_api_check
from prospection.storage.secret_box import SecretBox

EVERY = timedelta(days=7)
GOOGLE_PROBE = "mairie Paris"  # toujours des résultats : rien trouvé = format changé
REGISTRY_PROBE = "Renault"
logger = logging.getLogger(__name__)


def _google_format(engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing,
                   now: datetime) -> str | None:  # fmt: skip
    """Une vraie page, aux mêmes champs que les campagnes ; dans le budget (sinon rien)."""
    key = read_key(engine, box, Service.GOOGLE)
    if key is None or not reserve_call(engine, pricing, None, now):
        return None
    page = search_page(client, key, GOOGLE_PROBE, None, None)
    if page.skipped or not page.places:
        return "réponse inattendue (format changé ?)"
    return None


def _registry_format(client: httpx.Client) -> str | None:
    return None if search_companies(client, REGISTRY_PROBE, None) else "aucun résultat lisible"


def _checks(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, now: datetime
) -> list[tuple[str, str]]:
    problems = []
    for service in Service:
        with engine.connect() as conn:
            stored = load_key(conn, service) is not None
        if stored:
            result = run_key_test(engine, box, service, client, now)
            if not result.ok:
                problems.append((service.label, result.message))
    probes: tuple[tuple[str, Callable[[], str | None]], ...] = (
        ("Google Maps", lambda: _google_format(engine, box, client, pricing, now)),
        ("Registre des entreprises", lambda: _registry_format(client)),
    )
    for label, probe in probes:
        try:
            problem = probe()
        except Exception as error:  # injoignable, refus, réponse illisible
            logger.warning("Vérification %s : %s", label, type(error).__name__)
            problem = "injoignable ou réponse illisible"
        if problem:
            problems.append((label, problem))
    return problems


def weekly_api_check(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, now: datetime
) -> bool:
    """Vrai si la vérification a tourné (une fois par semaine au plus)."""
    with engine.begin() as conn:
        if not claim_api_check(conn, now, EVERY):
            return False
    problems = _checks(engine, box, client, pricing, now)
    with engine.begin() as conn:
        for label, problem in problems:
            message = f"Vérification hebdomadaire · {label} : {problem}"
            add_alert(conn, f"api:{label}:{now:%Y-%m-%d}", "api", message, "/reglages/cles", now)
    return True
