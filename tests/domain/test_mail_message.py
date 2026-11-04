"""C146, C148 : message envoyé (texte simple, désinscription toujours ajoutée, en-têtes sûrs)."""

import hashlib
from email import message_from_bytes, policy

import pytest

from prospection.domain.mail_message import (
    InvalidMail,
    build_message,
    check_draft,
    email_fingerprint,
)

LINK = "https://prospection.up.railway.app/desinscription/abc"


def parsed(raw: bytes):  # type: ignore[no-untyped-def]
    return message_from_bytes(raw, policy=policy.default)


def test_C146_plain_text_with_unsubscribe_footer_and_headers() -> None:
    raw = build_message("Kenny Pignolet", "kapignolet18@gmail.com", "contact@martin.fr",
                        "Martin : 1 point", "Bonjour,\n\nTexte.", LINK)  # fmt: skip
    message = parsed(raw)
    assert message["To"] == "contact@martin.fr"
    assert message["From"] == "Kenny Pignolet <kapignolet18@gmail.com>"
    assert message["List-Unsubscribe"] == f"<{LINK}>"
    assert message["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    body = message.get_content()
    assert body.startswith("Bonjour,\n\nTexte.") and LINK in body
    assert "Un clic suffit" in body and message.get_content_type() == "text/plain"


def test_C146_header_injection_is_impossible() -> None:
    raw = build_message("Kenny\r\nBcc: x@y.fr", "k@gmail.com", "a@b.fr",
                        "Objet\nBcc: x@y.fr", "Corps", LINK)  # fmt: skip
    message = parsed(raw)
    assert message["Bcc"] is None and "\n" not in message["Subject"]


def test_C146_draft_checked_before_sending() -> None:
    assert check_draft(" Objet ", "Corps\r\n") == ("Objet", "Corps")
    with pytest.raises(InvalidMail, match="objet"):
        check_draft("", "Corps")
    with pytest.raises(InvalidMail, match="texte"):
        check_draft("Objet", "   ")
    with pytest.raises(InvalidMail, match="long"):
        check_draft("Objet", "x" * 20_001)


def test_C148_fingerprint_ignores_case_and_spaces_and_needs_the_secret() -> None:
    pepper = b"secret-de-l-app"
    same = email_fingerprint(" Contact@Martin.FR ", pepper)
    assert same == email_fingerprint("contact@martin.fr", pepper)
    assert "martin" not in same
    plain = hashlib.sha256(b"contact@martin.fr").hexdigest()
    assert same != plain != email_fingerprint("contact@martin.fr", b"autre")  # salée
