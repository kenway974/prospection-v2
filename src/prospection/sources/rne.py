"""Registre national des entreprises (INPI) : objet social, activités déclarées, noms de
domaine (C150). Gratuit avec un compte data.inpi.fr (identifiants « email:motdepasse »).

Format repris du modèle public d'annuaire-entreprises (search-infra, rne_model.py) : contenu
dans formality.content, sous personneMorale, personnePhysique ou exploitation. Chaque champ est
validé ; un champ absent reste inconnu.
"""

from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from prospection.domain.key_check import KeyCheck, unexpected
from prospection.domain.place import clip
from prospection.http_client import json_object, send
from prospection.sources.rne_models import (
    Activity,
    Company,
    Description,
    Establishment,
    Identity,
    Person,
)

BASE = "https://registre-national-entreprises.inpi.fr/api"
LABEL = "INPI (registre national)"
MAX_ACTIVITIES = 5
FORMS = {"ARTISANALE": "artisanale", "COMMERCIALE": "commerciale", "AGRICOLE": "agricole",
         "LIBERALE_REGLEMENTEE": "libérale réglementée", "AGENT_COMMERCIAL": "agent commercial",
         "LIBERALE_NON_REGLEMENTEE": "libérale non réglementée",
         "ARTISANALE_REGLEMENTEE": "artisanale réglementée"}  # fmt: skip


class RneUnavailable(Exception):
    """L'INPI ne répond pas, demande de ralentir ou répond de façon inattendue."""


class RneRefused(Exception):
    """Identifiants INPI refusés."""


class RneExpired(Exception):
    """Jeton INPI expiré : se reconnecter."""


@dataclass(frozen=True)
class RneDetails:
    purpose: str | None
    activities: tuple[str, ...]
    domains: tuple[str, ...]


def rne_login(client: httpx.Client, username: str, password: str) -> str:
    body = {"username": username, "password": password}
    response = send(client, "POST", f"{BASE}/sso/login", LABEL, json=body)
    if isinstance(response, KeyCheck) or response.status_code == 429 or response.status_code >= 500:
        raise RneUnavailable
    token = (json_object(response) or {}).get("token") if response.status_code == 200 else None
    if not isinstance(token, str) or not token:
        raise RneRefused
    return token


def _activity(a: Activity) -> str | None:
    text = clip(a.descriptionDetaillee, 300)
    if not text:
        return None
    form = a.formeExercice or ""
    label = FORMS.get(form, form.replace("_", " ").lower())
    return f"{text} ({label})" if label else text


def _details(person: Person) -> RneDetails:
    identity, place = (
        person.identite or Identity(),
        person.etablissementPrincipal or Establishment(),
    )
    purpose = clip((identity.description or Description()).objet, 1000)
    activities = [x for a in (place.activites or [])[:20] if (x := _activity(a))]
    domains = [
        clip(d.nomDomaine, 200)
        for d in [*(identity.nomsDeDomaine or []), *(place.nomsDeDomaine or [])]
    ]
    unique_domains = tuple(dict.fromkeys(d.lower() for d in domains if d))
    unique_activities = tuple(dict.fromkeys(activities))
    return RneDetails(purpose or None, unique_activities[:MAX_ACTIVITIES],
                      unique_domains[:MAX_ACTIVITIES])  # fmt: skip


def rne_company(client: httpx.Client, token: str, siren: str) -> RneDetails | None:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    response = send(client, "GET", f"{BASE}/companies/{siren}", LABEL, headers=headers)
    if isinstance(response, KeyCheck) or response.status_code == 429 or response.status_code >= 500:
        raise RneUnavailable
    if response.status_code in (401, 403):
        raise RneExpired
    if response.status_code == 404:
        return None
    try:
        content = Company.model_validate(json_object(response)).formality.content
    except ValidationError:
        raise RneUnavailable from None
    person = content.personneMorale or content.personnePhysique or content.exploitation
    return _details(person) if person else None


def split_key(key: str) -> tuple[str, str] | None:
    """« email:motdepasse » → (email, mot de passe)."""
    username, _, password = key.partition(":")
    return (username, password) if username and password else None


def check_inpi_key(client: httpx.Client, key: str) -> KeyCheck:
    pair = split_key(key)
    if pair is None:
        return KeyCheck(False, "Saisissez « email:motdepasse » (identifiants de data.inpi.fr).")
    try:
        rne_login(client, *pair)
    except RneRefused:
        return KeyCheck(False, "Identifiants refusés par l'INPI : vérifiez-les sur data.inpi.fr.")
    except RneUnavailable:
        return unexpected(LABEL)
    return KeyCheck(True, "Identifiants INPI valides.")
