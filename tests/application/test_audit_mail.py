"""C145 à C147 : écran du mail d'audit, envoi depuis Gmail, note et rappel après l'envoi."""

from datetime import date

import pytest
from sqlalchemy import Engine

from prospection.application.audit_mail import MailBlocked, mail_screen, send_audit_mail
from prospection.application.prospect_card import card
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import (
    BASE,
    OAUTH,
    add_audited,
    google,
    ready,
    sent_raw,
)

PARIS = "Europe/Paris"


def screen(engine: Engine, pid: int):  # type: ignore[no-untyped-def]
    return mail_screen(engine, BOX, google()[0], OAUTH, BASE, pid, NOW)


def send(engine: Engine, pid: int, to: str = "contact@martin.fr", status: int = 200):  # type: ignore[no-untyped-def]
    client, recorder = google(status)
    send_audit_mail(engine, BOX, client, OAUTH, BASE, pid, to, "Objet", "Bonjour,\n\nTexte.",
                    NOW, PARIS)  # fmt: skip
    return recorder


def test_C145_draft_ready_with_usable_recipients(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    ready(mail_db)
    shown = screen(mail_db, pid)
    assert shown.blocked is None and shown.draft is not None
    assert shown.recipients == ["contact@martin.fr"]  # « noreply » écarté
    assert shown.draft.subject.endswith(": 2 points à améliorer sur votre site")
    assert "martin.fr" in shown.draft.body and "Un clic suffit" in shown.footer


def test_C145_says_what_to_do_when_something_is_missing(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    assert "Réglages → Mail d'audit" in (screen(mail_db, pid).blocked or "")
    no_site = add_audited(mail_db, None)
    ready(mail_db)
    assert "audit" in (screen(mail_db, no_site).blocked or "")


def test_C146_C147_sent_once_then_note_and_callback(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    ready(mail_db)
    recorder = send(mail_db, pid)
    raw = sent_raw(recorder)
    assert "To: contact@martin.fr" in raw and f"{BASE}/desinscription/" in raw
    shown = card(mail_db, pid, NOW, PARIS)
    assert shown.mail_sent_on == NOW
    assert shown.notes[0].text.startswith("Mail d'audit envoyé à contact@martin.fr")
    assert shown.action is not None and shown.action.kind == "rappeler"
    assert shown.action.due_date == date(2026, 10, 27)  # 25/10 + 2 jours (réglage)
    assert screen(mail_db, pid).sent_on == NOW
    with pytest.raises(MailBlocked, match="déjà"):
        send(mail_db, pid)


def test_C146_only_to_a_usable_address_of_this_prospect(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    ready(mail_db)
    for to in ("autre@ailleurs.fr", "noreply@martin.fr"):
        with pytest.raises(MailBlocked, match="adresse"):
            send(mail_db, pid, to)


def test_C146_gmail_failure_keeps_nothing(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    ready(mail_db)
    with pytest.raises(MailBlocked, match="reliez Gmail"):
        send(mail_db, pid, status=401)
    assert card(mail_db, pid, NOW, PARIS).mail_sent_on is None
    send(mail_db, pid)  # réessai possible
