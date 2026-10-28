"""C89 : un texte venu d'un site ou d'une API ne devient jamais une formule dans un tableur."""

import pytest

from prospection.domain.sheet_safe import safe_cell


@pytest.mark.parametrize("text", ["=1+1", "+33 6 12", "-2+3", "@SUM(A1)", "\t=1", "\r=1",
                                  '=HYPERLINK("http://x","clic")', "\x01=1", "  =1", "\n=1",
                                  "\uff1d1+1", "\uff0b1", "\uff201"])  # fmt: skip
def test_C89_formula_neutralized(text: str) -> None:
    assert str(safe_cell(text)).startswith("'")


def test_C89_plain_text_and_numbers_kept() -> None:
    assert safe_cell("Cuisines Martin") == "Cuisines Martin" and safe_cell(42) == 42
    assert safe_cell("A\x00B\x1bC") == "A B C" and safe_cell(None) == ""
