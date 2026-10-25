"""Plafond de dépense Google par mois (C07), en centimes.

0 € (par défaut) : l'app reste dans le quota gratuit mensuel de Google.
Au-delà de 0 : montant que l'app peut dépenser en plus de ce quota.
"""

import re

MAX_BUDGET_CENTS = 5_000
_AMOUNT = re.compile(r"-?\d+(?:[.,]\d{1,2})?")


class InvalidBudget(ValueError):
    """Montant refusé ; le message dit quoi saisir."""


def parse_budget(text: str) -> int:
    """« 0 », « 5 », « 12,50 » ou « 12.50 € » → centimes."""
    cleaned = "".join(text.replace("€", "").split())
    if not _AMOUNT.fullmatch(cleaned):
        raise InvalidBudget("Indiquez un montant en euros, par exemple 0 ou 5.")
    if cleaned.startswith("-"):
        raise InvalidBudget("Indiquez 0 € ou plus.")
    euros, _, cents = cleaned.replace(",", ".").partition(".")
    total = int(euros) * 100 + int(cents.ljust(2, "0") or 0)
    if total > MAX_BUDGET_CENTS:
        raise InvalidBudget("Le plafond est limité à 50 € par mois.")
    return total
