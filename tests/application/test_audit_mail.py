"""C145 à C147 : écran du mail d'audit, envoi depuis Gmail, note et rappel après l'envoi."""

from datetime import date

import pytest
from sqlalchemy import Engine

from prospection.application.audit_mail import MailBlocked, mail_screen, send_audit_mail
from prospection.application.audit_mail_context import load_context
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
    assert shown.draft.subject.endswith(": audit express de votre site, 3 points à corriger")
    assert "martin.fr" in shown.draft.body and "Un clic suffit" in shown.footer


def test_C145_says_what_to_do_when_something_is_missing(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    assert "Réglages → Mail d'audit" in (screen(mail_db, pid).blocked or "")
    not_read = add_audited(mail_db, None)  # site pas encore lu : fiche Google seule (C161)
    ready(mail_db)
    shown = screen(mail_db, not_read)
    assert shown.draft is not None and "Aucun email utilisable" in (shown.blocked or "")


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


def test_C145_old_audit_never_claims_a_missing_form(mail_db: Engine) -> None:
    """Audits d'avant C137 : la détection manquait des formulaires, on ne l'affirme pas."""
    import dataclasses

    from tests.application.mail_helpers import AUDIT, SITE

    old = dataclasses.replace(AUDIT, form_place=None, codes=("no_form", "no_social"))
    pid = add_audited(mail_db, dataclasses.replace(SITE, audit=old))
    ready(mail_db)
    ctx = load_context(mail_db, BOX, google()[0], OAUTH, BASE, pid, NOW)
    assert "no_form" not in [p.code for p in ctx.points]  # plus rien de sûr à dire


def test_C146_uncertain_send_is_kept_never_sent_twice(mail_db: Engine) -> None:
    import httpx

    from tests.fake_http import fake_client

    pid = add_audited(mail_db)
    ready(mail_db)

    def lost(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "court"})
        raise httpx.ReadTimeout("réponse perdue", request=request)

    with pytest.raises(MailBlocked, match="Messages envoyés"):
        send_audit_mail(mail_db, BOX, fake_client(lost)[0], OAUTH, BASE, pid,
                        "contact@martin.fr", "Objet", "Texte", NOW, PARIS)  # fmt: skip
    assert card(mail_db, pid, NOW, PARIS).mail_sent_on == NOW
    with pytest.raises(MailBlocked, match="déjà"):
        send(mail_db, pid)


def test_C146_same_address_never_written_twice(mail_db: Engine) -> None:
    ready(mail_db)
    send(mail_db, add_audited(mail_db))
    assert screen(mail_db, add_audited(mail_db)).recipients == []
