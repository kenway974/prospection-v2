"""Textes des SMS (C179), lus dans `data/sms_rules.yaml` et validés au démarrage.

Chaque texte rempli tient en un seul SMS : alphabet SMS de base (GSM 03.38), 160 caractères
dont 20 gardés pour la mention STOP. Les noms d'entreprise hors de cet alphabet sont
simplifiés (« Crêperie » → « Creperie ») ; un nom trop long est retiré, jamais coupé.
"""

import unicodedata
from functools import cache
from importlib import resources
from string import Formatter

import yaml
from pydantic import BaseModel, ValidationError

SMS_LENGTH, STOP_RESERVE = 160, 20
BUDGET = SMS_LENGTH - STOP_RESERVE
KINDS = ("mail", "bloque", "sans_mail", "relance_bloque")
VARIABLES = frozenset({"salutation", "probleme", "telephone"})
MAX_PROBLEM = 45
HELLO = "Bonjour"
SAMPLE_PHONE = "+33 6 12 34 56 78"
_GSM = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "ÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
_LOOKALIKE = {  # apostrophes et guillemets typographiques, tirets, espaces insécables…
    "\u2019": "'",
    "\u2018": "'",
    "\u00ab": '"',
    "\u00bb": '"',
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u0153": "oe",
    "\u0152": "OE",
    "\u00a0": " ",
    "\u202f": " ",
    "\u2026": "...",
}


class InvalidSmsRules(ValueError):
    """Le fichier des textes des SMS est mal formé."""


class SmsRules(BaseModel):
    textes: dict[str, str]
    defaut: str = "quelques points simples à corriger"
    problemes: dict[str, str] = {}


def gsm_safe(text: str) -> bool:
    return all(c in _GSM for c in text)


def simplify(text: str) -> str:
    """Caractères hors de l'alphabet SMS remplacés par leur lettre de base, sinon retirés."""
    out = []
    for char in text:
        char = _LOOKALIKE.get(char, char)
        if not all(c in _GSM for c in char):
            char = "".join(c for c in unicodedata.normalize("NFKD", char) if c in _GSM)
        out.append(char)
    return " ".join("".join(out).split())


def _render(template: str, hello: str, problem: str, phone: str) -> str:
    return template.format(salutation=hello, probleme=problem, telephone=phone)


def parse_sms_rules(raw: object) -> SmsRules:
    try:
        rules = SmsRules.model_validate(raw)
    except ValidationError as error:
        raise InvalidSmsRules(f"Textes des SMS mal formés : {error}") from None
    if set(rules.textes) != set(KINDS):
        raise InvalidSmsRules(f"Textes des SMS attendus : {', '.join(KINDS)}.")
    phrases = [rules.defaut, *rules.problemes.values()]
    for phrase in phrases:
        if len(phrase) > MAX_PROBLEM or not gsm_safe(phrase):
            raise InvalidSmsRules(f"Phrase de SMS « {phrase} » : à raccourcir ({MAX_PROBLEM} "
                                  "caractères au plus, alphabet SMS de base).")  # fmt: skip
    longest = max(phrases, key=len)
    for kind, template in rules.textes.items():
        names = {n for _, n, _, _ in Formatter().parse(template) if n is not None}
        if unknown := names - VARIABLES:
            raise InvalidSmsRules(f"SMS « {kind} » : variable inconnue {sorted(unknown)}.")
        filled = _render(template, HELLO, longest, SAMPLE_PHONE)
        if not gsm_safe(filled):
            raise InvalidSmsRules(f"SMS « {kind} » : caractère hors de l'alphabet SMS.")
        if len(filled) > BUDGET:
            raise InvalidSmsRules(f"SMS « {kind} » trop long : à raccourcir ({BUDGET} au plus).")
    return rules


@cache
def load_sms_rules() -> SmsRules:
    text = resources.files("prospection.data").joinpath("sms_rules.yaml").read_text("utf-8")
    return parse_sms_rules(yaml.safe_load(text))


def fill_sms(kind: str, company: str, point: str | None, phone: str) -> str:
    """Texte prêt à partir. `point` : code du premier point de l'audit. Le nom n'apparaît que
    s'il tient en entier : « Bonjour » seul vaut mieux qu'un nom coupé."""
    rules = load_sms_rules()
    template, problem = rules.textes[kind], rules.problemes.get(point or "", rules.defaut)
    named, phone = f"{HELLO} {simplify(company)}".strip(), simplify(phone)
    text = _render(template, named, problem, phone)
    return text if len(text) <= BUDGET else _render(template, HELLO, problem, phone)
