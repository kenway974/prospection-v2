"""C53, C54 : chaque email vérifié ; nominatif ou générique."""

import pytest

from prospection.domain.email_check import (
    DOUBTFUL,
    INVALID,
    UNCHECKED,
    VALID,
    check_email,
    email_domain,
)


@pytest.mark.parametrize(
    ("email", "reason"),
    [("pas-un-email", "syntaxe incorrecte"), ("noreply@martin.fr", "« ne pas répondre »"),
     ("contact@example.com", "adresse factice"), ("jean@gmial.com", "@gmail.com ?"),
     ("x@yopmail.com", "adresse jetable"), ("", "adresse vide")],
)  # fmt: skip
def test_C53_unusable_email_said_why(email: str, reason: str) -> None:
    result = check_email(email, None)
    assert result.status == INVALID and reason in result.reason


def test_C53_mail_server_decides_between_valid_and_doubtful() -> None:
    assert check_email("jean.martin@martin.fr", "mx").status == VALID
    no_mx = check_email("jean.martin@martin.fr", "aucun")
    assert no_mx.status == DOUBTFUL and "serveur mail" in no_mx.reason
    assert check_email("jean.martin@martin.fr", "inexistant").status == INVALID
    assert check_email("jean.martin@martin.fr", None).status == UNCHECKED


def test_C54_generic_or_named() -> None:
    assert check_email("contact@martin.fr", "mx").generic
    assert check_email("Info+devis@martin.fr", "mx").generic
    assert not check_email("jean.martin@martin.fr", "mx").generic


def test_domain_of_an_email() -> None:
    assert email_domain("Jean@Martin.FR") == "martin.fr"
    assert email_domain("pas-un-email") is None
