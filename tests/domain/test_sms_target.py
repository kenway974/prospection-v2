"""C176 : un SMS ne part que vers un mobile français."""

from prospection.domain.sms_target import french_mobile


def test_C176_first_french_mobile_in_international_form() -> None:
    assert french_mobile(["04 67 12 34 56", "06 81 78 73 25"]) == "+33681787325"
    assert french_mobile(["+33 7 81 23 45 67"]) == "+33781234567"


def test_C176_landlines_foreign_and_garbage_are_refused() -> None:
    assert french_mobile(["04 67 12 34 56", "09 72 00 00 00"]) is None
    assert french_mobile(["+32 470 12 34 56"]) is None  # mobile belge
    assert french_mobile(["", "abc", "06"]) is None
