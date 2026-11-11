"""Relecture du groupe C182 à C185 : jamais un second mail à la même entreprise, jamais à un
entrepreneur non diffusible, rien de perdu ni de répété en fin de campagne."""

import dataclasses

from sqlalchemy import Engine, text

from prospection.application.campaign_mail import queue_campaign_mails
from prospection.domain.criteria import Verdict
from prospection.domain.mail_message import email_fingerprint
from prospection.domain.site_contacts import Contacts
from prospection.storage.audit_mails import record_send
from prospection.storage.campaigns import create_campaign
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import BOX, NOW, request
from tests.application.mail_helpers import SITE, ready
from tests.storage.test_campaigns import PLACE, STEPS

TWO = dataclasses.replace(SITE, contacts=Contacts(("contact@martin.fr", "info@martin.fr"), (), ()))


def _campaign(engine: Engine, status: str = "sûr") -> tuple[int, int]:
    with engine.begin() as conn:
        cid = create_campaign(conn, request(), STEPS, NOW)
        insert_prospect(conn, cid, PLACE, "plombier", Verdict(True, (), ()), NOW, TWO)
        pid = int(conn.execute(text("SELECT max(id) FROM prospects")).scalar_one())
        conn.execute(text("UPDATE prospects SET registry_status = :s WHERE id = :p"),
                     {"s": status, "p": pid})  # fmt: skip
    return cid, pid


def test_C182_same_company_found_again_never_gets_a_second_mail(mail_db: Engine) -> None:
    ready(mail_db)
    c1, p1 = _campaign(mail_db)
    assert queue_campaign_mails(mail_db, BOX, c1, NOW) == 1
    with mail_db.begin() as conn:  # le mail de la 1re campagne part à contact@
        conn.execute(text("UPDATE mail_queue SET status = 'envoye'"))
        record_send(conn, p1, email_fingerprint("contact@martin.fr", BOX.pepper), "t1", NOW)
    c2, _ = _campaign(mail_db)  # programme : la même fiche Google retrouvée
    assert queue_campaign_mails(mail_db, BOX, c2, NOW) == 0


def test_C182_already_called_company_is_left_alone(mail_db: Engine) -> None:
    ready(mail_db)
    _, p1 = _campaign(mail_db)
    with mail_db.begin() as conn:
        conn.execute(text("UPDATE prospects SET status = 'pas intéressé' WHERE id = :p"),
                     {"p": p1})  # fmt: skip
    c2, _ = _campaign(mail_db)
    assert queue_campaign_mails(mail_db, BOX, c2, NOW) == 0


def test_C168_never_to_a_non_publishable_entrepreneur(mail_db: Engine) -> None:
    ready(mail_db)
    cid, _ = _campaign(mail_db, status="non diffusible")
    assert queue_campaign_mails(mail_db, BOX, cid, NOW) == 0


def test_C182_campaign_mails_queued_once_even_if_replayed(mail_db: Engine) -> None:
    ready(mail_db)
    cid, _ = _campaign(mail_db)
    assert queue_campaign_mails(mail_db, BOX, cid, NOW) == 1
    assert queue_campaign_mails(mail_db, BOX, cid, NOW) == 0
    with mail_db.connect() as conn:
        query = text(
            "SELECT count(*) FROM campaign_events WHERE campaign_id = :c "
            "AND message LIKE 'Mail d''audit%'"
        )
        lines = conn.execute(query, {"c": cid}).scalar_one()
    assert lines == 1


def test_C182_campaign_missed_by_a_crash_is_caught_up(mail_db: Engine) -> None:
    from prospection.application.campaign_mail import catch_up_campaign_mails

    ready(mail_db)
    cid, _ = _campaign(mail_db)
    with mail_db.begin() as conn:
        conn.execute(text("UPDATE campaigns SET status = 'done' WHERE id = :c"), {"c": cid})
    assert catch_up_campaign_mails(mail_db, BOX, NOW) == 1
    assert catch_up_campaign_mails(mail_db, BOX, NOW) == 0


def test_C182_campaign_journal_never_counts_an_sms_without_mobile(mail_db: Engine) -> None:
    from tests.application.test_sms_batch import sms_ready

    sms_ready(mail_db)
    cid, pid = _campaign(mail_db, status="")
    landline = text(
        "UPDATE prospects SET registry_status = NULL, "
        "data_json = jsonb_set(data_json, '{phone}', to_jsonb(CAST(:n AS text))) WHERE id = :p"
    )
    with mail_db.begin() as conn:
        conn.execute(landline, {"n": "04 72 00 00 00", "p": pid})
    queue_campaign_mails(mail_db, BOX, cid, NOW)
    with mail_db.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM sms_queue")).scalar_one() == 0
