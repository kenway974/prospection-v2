"""C175 : réglages des SMS : activés ou non, nom d'expéditeur, plafond par jour."""

import pytest

from prospection.domain.sms_settings import InvalidSmsSettings, clean_sms_settings


def test_C175_valid_settings() -> None:
    s = clean_sms_settings("on", " Kenny ", "25")
    assert (s.enabled, s.sender, s.daily_limit) == (True, "Kenny", 25)
    assert clean_sms_settings("", "Kenny", "30").enabled is False


@pytest.mark.parametrize(
    ("sender", "limit", "field"),
    [("", "30", "sender"), ("Kenny Pignolet", "30", "sender"), ("Kenny!", "30", "sender"),
     ("12345", "30", "sender"), ("Kenny", "0", "limit"), ("Kenny", "abc", "limit")],
)  # fmt: skip
def test_C175_wrong_inputs_say_what_to_do(sender: str, limit: str, field: str) -> None:
    with pytest.raises(InvalidSmsSettings) as error:
        clean_sms_settings("on", sender, limit)
    assert field in error.value.errors
