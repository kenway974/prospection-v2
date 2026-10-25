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
