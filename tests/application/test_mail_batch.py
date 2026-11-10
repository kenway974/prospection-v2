"""C168 : envoi du mail d'audit à une sélection : confirmation avec les prospects écartés et
leur raison, puis mise en file (rien ne part depuis l'interface)."""

import dataclasses

from sqlalchemy import Engine

from prospection.application.mail_batch import batch_preview, queue_batch
from prospection.storage.mail_queue import pending_ids
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import SITE, add_audited, ready
from tests.application.test_audit_mail import send


def _opt_out(engine: Engine, email: str) -> None:
    from prospection.domain.mail_message import email_fingerprint

    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO mail_optouts (email_hash, created_at) VALUES (%(h)s, now())",
            {"h": email_fingerprint(email, BOX.pepper)},
        )


def test_C168_each_prospect_says_if_the_mail_leaves_and_why_not(mail_db: Engine) -> None:
    ready(mail_db)
    ok = add_audited(mail_db, contacts_email="ok@martin.fr")
    no_report = add_audited(mail_db, site=None)
    sent = add_audited(mail_db, contacts_email="deja@martin.fr")
    send(mail_db, sent, to="deja@martin.fr")
    out = add_audited(mail_db, contacts_email="stop@martin.fr")
    _opt_out(mail_db, "stop@martin.fr")
    platform = add_audited(mail_db, dataclasses.replace(SITE, unconfirmed=True), "pf@martin.fr")
    preview = batch_preview(mail_db, BOX, [ok, no_report, sent, out, platform])
    assert preview.blocked is None
    reasons = {row.prospect_id: row.reason for row in preview.rows}
    assert reasons[ok] is None
    assert reasons[no_report] == "pas encore d'audit"
    assert reasons[sent] == "mail d'audit déjà envoyé"
    assert reasons[out] == "désinscrit"
    assert reasons[platform] == "site à vérifier (plateforme ?)"
    assert [r.email for r in preview.rows if r.prospect_id == ok] == ["ok@martin.fr"]


def test_C168_whole_batch_blocked_without_gmail(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    preview = batch_preview(mail_db, BOX, [pid])
    assert (
        (preview.blocked is not None
        and "Gmail" in preview.blocked)
        or "Réglages" in str(preview.blocked)
    )


def test_C168_only_the_mailable_ones_are_queued_once(mail_db: Engine) -> None:
    ready(mail_db)
    ok = add_audited(mail_db, contacts_email="ok@martin.fr")
    no_report = add_audited(mail_db, site=None)
    assert queue_batch(mail_db, BOX, [ok, no_report], NOW) == 1
    assert queue_batch(mail_db, BOX, [ok], NOW) == 0  # déjà en file
    with mail_db.connect() as conn:
        assert pending_ids(conn) == [ok]
