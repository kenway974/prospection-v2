"""Budget Google mensuel (C07) : saisie et reste disponible, en centimes."""

import re

MAX_BUDGET_CENTS = 100_000
_AMOUNT = re.compile(r"-?\d+(?:[.,]\d{1,2})?")


class InvalidBudget(ValueError):
    """Montant refusé ; le message dit quoi saisir."""


def parse_budget(text: str) -> int:
    """« 25 », « 12,50 » ou « 12.50 € » → centimes."""
    cleaned = text.replace("€", "").replace(" ", "").strip()
    if not _AMOUNT.fullmatch(cleaned):
        raise InvalidBudget("Indiquez un montant en euros, par exemple 25 ou 12,50.")
    euros, _, cents = cleaned.replace(",", ".").partition(".")
    sign = -1 if euros.startswith("-") else 1
    total = int(euros.lstrip("-")) * 100 + int(cents.ljust(2, "0") or 0)
    total *= sign
    if total <= 0:
        raise InvalidBudget("Indiquez un montant supérieur à 0 €.")
    if total > MAX_BUDGET_CENTS:
        raise InvalidBudget("Le budget mensuel est limité à 1 000 €.")
    return total


def remaining_cents(budget_cents: int, spent_cents: int) -> int:
    """Ce qu'il reste à dépenser ce mois-ci ; jamais négatif."""
    return max(0, budget_cents - spent_cents)
