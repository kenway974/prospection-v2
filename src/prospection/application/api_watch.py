"""Vérification hebdomadaire des vraies API (C99), hors CI, par la tâche de fond : clés
encore acceptées et réponses toujours au format attendu ; sinon, une alerte. Une panne
passagère est retentée une heure plus tard et signalée seulement si elle persiste.
Limite : Notion n'est vérifié que par le test de sa clé."""

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
from prospection.storage.maintenance import claim_api_check, note_api_outage, reset_api_outages
from prospection.storage.secret_box import SecretBox

EVERY, RETRY = timedelta(days=7), timedelta(hours=1)
GOOGLE_PROBE = "mairie Paris"  # toujours des résultats : rien de lisible = format changé
REGISTRY_PROBE = "Renault"
OUTAGE = "injoignable ou réponse illisible, deux fois de suite"
logger = logging.getLogger(__name__)
Problem = tuple[str, str]


def _google_format(engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing,
                   now: datetime) -> str | None:  # fmt: skip
    """Une vraie page, aux mêmes champs que les campagnes ; dans le budget (sinon rien)."""
    key = read_key(engine, box, Service.GOOGLE)
    if key is None or not reserve_call(engine, pricing, None, now):
        return None
    page = search_page(client, key, GOOGLE_PROBE, None, None)
    return None if page.places else "aucun établissement lisible (format changé ?)"


def _registry_format(client: httpx.Client) -> str | None:
    return None if search_companies(client, REGISTRY_PROBE, None) else "aucun résultat lisible"


def _key_problems(
    engine: Engine, box: SecretBox, client: httpx.Client, now: datetime
) -> list[Problem]:
    problems = []
    for service in Service:
        with engine.connect() as conn:
            stored = load_key(conn, service) is not None
        if stored:
            result = run_key_test(engine, box, service, client, now)
            if not result.ok:
                problems.append((service.label, result.message))
    return problems


def _checks(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, now: datetime
) -> tuple[list[Problem], list[str]]:
    """Problèmes sûrs (clé refusée, format changé) et services en panne passagère."""
    problems = _key_problems(engine, box, client, now)
    probes: list[tuple[str, Callable[[], str | None]]] = [
        ("Registre des entreprises", lambda: _registry_format(client))
    ]
    if not any(label == Service.GOOGLE.label for label, _ in problems):  # clé refusée : rien
        probes.append(("Google Maps", lambda: _google_format(engine, box, client, pricing, now)))
    outages = []
    for label, probe in probes:
        try:
            problem = probe()
        except Exception as error:  # injoignable, trop sollicité, réponse illisible
            logger.warning("Vérification %s : %s", label, type(error).__name__)
            outages.append(label)
            continue
        if problem:
            problems.append((label, problem))
    return problems, outages


def weekly_api_check(
    engine: Engine, box: SecretBox, client: httpx.Client, pricing: Pricing, now: datetime
) -> bool:
    """Vrai si la vérification a tourné (une fois par semaine, plus un nouvel essai)."""
    with engine.begin() as conn:
        if not claim_api_check(conn, now, EVERY):
            return False
    problems, outages = _checks(engine, box, client, pricing, now)
    with engine.begin() as conn:
        if outages and note_api_outage(conn, now + RETRY, EVERY) >= 2:
            problems += [(label, OUTAGE) for label in outages]
            outages = []
        if not outages:
            reset_api_outages(conn)
        for label, problem in problems:
            message = f"Vérification hebdomadaire · {label} : {problem}"
            add_alert(conn, f"api:{label}:{now:%Y-%m-%d}", "api", message, "/reglages/cles", now)
    return True
