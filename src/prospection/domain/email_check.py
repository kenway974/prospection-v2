"""Vérifier un email avant de le noter ou de l'exporter (C53, C54).

Aucun envoi, aucune sonde SMTP : syntaxe, adresses inutiles (« ne pas répondre », factices,
jetables, fautes de frappe), puis le serveur mail du domaine, vérifié à part par la tâche
de fond et passé ici en paramètre. Repris de prospection-bot (services/email_check.py,
version 530ba12) ; listes dans data/email_rules.yaml.
"""

import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

import yaml
from pydantic import BaseModel

VALID, DOUBTFUL, INVALID, UNCHECKED = "valide", "douteux", "invalide", "pas encore vérifié"
# Serveur mail du domaine (résultat de la vérification DNS) : « mx », « aucun », « inexistant »
_EMAIL = re.compile(
    r"[a-z0-9!#$%&'*+/=?^_`{|}~-]{1,64}(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]{1,64}){0,8}"
    r"@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){1,8}[a-z]{2,63}"
)


class _Rules(BaseModel):
    noreply: frozenset[str]
    placeholder_local: frozenset[str]
    placeholder_domains: frozenset[str]
    generic_local: frozenset[str]
    typos: dict[str, str]
    disposable: frozenset[str]


@cache
def rules() -> _Rules:
    text = resources.files("prospection.data").joinpath("email_rules.yaml").read_text("utf-8")
    return _Rules.model_validate(yaml.safe_load(text))


@dataclass(frozen=True)
class EmailCheck:
    email: str
    status: str
    reason: str
    generic: bool = False


def is_email(address: str) -> bool:
    """Syntaxe d'un email (en minuscules), la même partout : saisie, site, fiche."""
    return len(address) <= 254 and _EMAIL.fullmatch(address) is not None


def email_domain(email: str) -> str | None:
    address = email.strip().lower()
    return address.rsplit("@", 1)[1] if _EMAIL.fullmatch(address) else None


def _unusable(local: str, domain: str) -> str | None:
    r = rules()
    if local in r.noreply:
        return "adresse « ne pas répondre » : personne ne la lit"
    if domain in r.placeholder_domains or local in r.placeholder_local:
        return "adresse factice"
    if domain in r.typos:
        return f"faute de frappe probable (@{r.typos[domain]} ?)"
    if domain in r.disposable:
        return "adresse jetable"
    return None


def check_email(email: str, mail_server: str | None) -> EmailCheck:
    """`mail_server` : résultat DNS du domaine, ou None s'il n'est pas encore vérifié."""
    address = email.strip().lower()
    if not address:
        return EmailCheck(email, INVALID, "adresse vide")
    if not is_email(address):
        return EmailCheck(email, INVALID, "syntaxe incorrecte")
    local, domain = address.rsplit("@", 1)
    base = local.split("+", 1)[0]
    problem = _unusable(base, domain)
    if problem:
        return EmailCheck(address, INVALID, problem)
    generic = base in rules().generic_local
    kind = "générique (pas forcément le décideur)" if generic else "nominative"
    if mail_server == "mx":
        return EmailCheck(address, VALID, f"serveur mail déclaré · adresse {kind}", generic)
    if mail_server == "inexistant":
        return EmailCheck(address, INVALID, "domaine inexistant", generic)
    if mail_server == "aucun":
        return EmailCheck(address, DOUBTFUL, "le domaine n'a pas de serveur mail", generic)
    return EmailCheck(address, UNCHECKED, f"serveur mail pas encore vérifié · {kind}", generic)
