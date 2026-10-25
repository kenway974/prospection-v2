"""C07 : plafond de dépense Google par mois (0 € = rester dans le gratuit de Google)."""

import pytest

from prospection.domain.budget import InvalidBudget, parse_budget


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("25", 2500),
        ("12,50", 1250),
        ("12.50", 1250),
        (" 7,5 € ", 750),
        ("0", 0),
        ("50", 5000),
        ("0\u00a0€", 0),
    ],
)
def test_C07_budget_parsing(text: str, cents: int) -> None:
    assert parse_budget(text) == cents


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("-5", "Indiquez 0 € ou plus."),
        ("50,01", "Le plafond est limité à 50 € par mois."),
        ("1000", "Le plafond est limité à 50 € par mois."),
        ("beaucoup", "Indiquez un montant en euros, par exemple 0 ou 5."),
        ("", "Indiquez un montant en euros, par exemple 0 ou 5."),
        ("12,345", "Indiquez un montant en euros, par exemple 0 ou 5."),
    ],
)
def test_C07_invalid_budget(text: str, message: str) -> None:
    with pytest.raises(InvalidBudget, match=message):
        parse_budget(text)
