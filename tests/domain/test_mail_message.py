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
    plain = message.get_body(("plain",))
    assert plain is not None
    body = plain.get_content()
    assert body.startswith("Bonjour,\n\nTexte.") and LINK in body and "Un clic suffit" in body


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


def test_C146_html_version_keeps_whole_sentences_and_stays_safe() -> None:
    """Gmail recoupe les mails en texte simple vers 76 caractères : la version HTML garde
    les phrases entières ; tout y est échappé, seuls les liens deviennent cliquables."""
    body = (
        "Bonjour,\n\n" + "Une phrase longue " * 10 + "\n\nVoir https://kenny.dev/a?b=1&c=2 <b>x</b>"
    )
    message = parsed(build_message("Kenny", "k@gmail.com", "a@b.fr", "Objet", body, LINK))
    plain = message.get_body(("plain",))
    rich = message.get_body(("html",))
    assert plain is not None and rich is not None
    assert "Une phrase longue " * 10 in plain.get_content()
    html = rich.get_content()
    assert "<p>" + ("Une phrase longue " * 10).strip() + "</p>" in html
    assert '<a href="https://kenny.dev/a?b=1&amp;c=2">https://kenny.dev/a?b=1&amp;c=2</a>' in html
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "<b>" not in html
    assert f'<a href="{LINK}">' in html  # désinscription cliquable aussi
