"""C144 : réglages du mail d'audit, validés avec des messages qui disent quoi faire."""

import pytest

from prospection.domain.audit_mail import MailSender
from prospection.domain.mail_settings import (
    InvalidMailSettings,
    MailSettings,
    clean_mail_settings,
    sender_of,
)


def test_C144_settings_cleaned() -> None:
    settings = clean_mail_settings(" Kenny  Pignolet ", " 06 12 34 56 78 ", "https://kenny.dev ",
                                   "", "3")  # fmt: skip
    assert settings == MailSettings("Kenny Pignolet", "06 12 34 56 78", "https://kenny.dev",
                                    None, 3)  # fmt: skip
    assert sender_of(settings) == MailSender("Kenny Pignolet", "06 12 34 56 78",
                                             "https://kenny.dev", None)  # fmt: skip


@pytest.mark.parametrize(
    ("fields", "field"),
    [
        (("", "", "https://k.dev", "", "2"), "name"),
        (("Kenny", "", "kenny.dev", "", "2"), "portfolio"),
        (("Kenny", "", "javascript:alert(1)", "", "2"), "portfolio"),
        (("Kenny", "", "https://k.dev", "http://calendly.com/k", "2"), "calendly"),
        (("Kenny", "", "https://k.dev", "", "4"), "days"),
        (("Kenny", "", "https://k.dev", "", "deux"), "days"),
        (("Kenny", "x" * 31, "https://k.dev", "", "2"), "phone"),
    ],
)
def test_C144_bad_settings_refused(fields: tuple[str, ...], field: str) -> None:
    with pytest.raises(InvalidMailSettings) as error:
        clean_mail_settings(*fields)
    assert field in error.value.errors


def test_C144_no_sender_until_name_and_portfolio_are_set() -> None:
    assert sender_of(MailSettings(None, None, None, None, 2)) is None
