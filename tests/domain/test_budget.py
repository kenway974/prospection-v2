"""C07 : budget Google mensuel."""

import pytest

from prospection.domain.budget import InvalidBudget, parse_budget


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("25", 2500),
        ("12,50", 1250),
        ("12.50", 1250),
        (" 7,5 € ", 750),
        ("1000", 100_000),
        ("1\u00a0000", 100_000),
        ("1\u202f000", 100_000),
    ],
)
def test_C07_budget_parsing(text: str, cents: int) -> None:
    assert parse_budget(text) == cents


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("0", "Indiquez un montant supérieur à 0 €."),
        ("-5", "Indiquez un montant supérieur à 0 €."),
        ("1000,01", "Le budget mensuel est limité à 1 000 €."),
        ("beaucoup", "Indiquez un montant en euros, par exemple 25 ou 12,50."),
        ("", "Indiquez un montant en euros, par exemple 25 ou 12,50."),
        ("12,345", "Indiquez un montant en euros, par exemple 25 ou 12,50."),
    ],
)
def test_C07_invalid_budget(text: str, message: str) -> None:
    with pytest.raises(InvalidBudget, match=message):
        parse_budget(text)
