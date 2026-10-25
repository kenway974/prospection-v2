"""C22 : distinguer mobile et fixe, y compris outre-mer."""

import pytest

from prospection.domain.phones import is_mobile


@pytest.mark.parametrize(
    ("number", "mobile"),
    [
        ("+33 6 12 34 56 78", True),
        ("06 12 34 56 78", True),
        ("+33 1 23 45 67 89", False),
        ("+262 692 12 34 56", True),
        ("0692 12 34 56", True),
        ("+262 262 21 00 00", False),
        ("0693 00 00 00", True),
        ("pas un numéro", False),
        ("", False),
    ],
)
def test_C22_reunion_0692_is_mobile(number: str, mobile: bool) -> None:
    assert is_mobile(number) is mobile


@pytest.mark.parametrize(
    ("number", "country", "mobile"),
    [
        ("+32 470 12 34 56", None, True), ("+32 4 222 33 44", None, False),
        ("+41 79 123 45 67", None, True), ("+41 22 123 45 67", None, False),
        ("+352 621 123 456", None, True), ("+377 6 12 34 56 78", None, True),
        ("0470 12 34 56", "BE", True), ("022 123 45 67", "CH", False),
    ],
)  # fmt: skip
def test_C124_belgian_swiss_luxembourg_monaco_numbers(
    number: str, country: str | None, mobile: bool
) -> None:
    assert is_mobile(number, country) is mobile
