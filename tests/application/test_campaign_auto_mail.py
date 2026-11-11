"""C182 : dès qu'une campagne est finie, le mail d'audit de chaque prospect retenu part en
file automatiquement (avec son SMS), avec les garde-fous de l'envoi groupé."""

import dataclasses

from sqlalchemy import Engine, text

from prospection.application.campaign_mail import queue_campaign_mails
from prospection.domain.criteria import Verdict
from prospection.storage.campaigns import create_campaign
from prospection.storage.mail_queue import pending_ids
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import BOX, NOW, request
from tests.application.mail_helpers import SITE, ready
from tests.application.test_sms_batch import sms_ready
from tests.storage.test_campaigns import PLACE, STEPS


def _campaign(engine: Engine) -> tuple[int, int, int]:
    """Campagne avec un prospect retenu et un écarté par les critères."""
    with engine.begin() as conn:
        cid = create_campaign(conn, request(), STEPS, NOW)
        for place_id, ok in (("kept", True), ("dropped", False)):
            place = dataclasses.replace(PLACE, place_id=place_id)
            insert_prospect(conn, cid, place, "plombier", Verdict(ok, (), ()), NOW, SITE)
        ids: dict[str, int] = dict(conn.execute(text("SELECT place_id, id FROM prospects "
                                                     "WHERE campaign_id = :c"),
                                {"c": cid}).all())  # fmt: skip
    return cid, ids["kept"], ids["dropped"]


def test_C182_retained_prospects_are_queued_at_the_end(mail_db: Engine) -> None:
    ready(mail_db)
    cid, kept, _ = _campaign(mail_db)
    assert queue_campaign_mails(mail_db, BOX, cid, NOW) == 1
    with mail_db.connect() as conn:
        assert pending_ids(conn) == [kept]
        events = conn.execute(text("SELECT message FROM campaign_events WHERE campaign_id = :c"),
                              {"c": cid}).scalars().all()  # fmt: skip
    assert any("Mail d'audit : 1 en file" in e for e in events)


def test_C182_without_gmail_the_journal_says_what_to_do(mail_db: Engine) -> None:
    cid, _, _ = _campaign(mail_db)
    assert queue_campaign_mails(mail_db, BOX, cid, NOW) == 0
    with mail_db.connect() as conn:
        events = conn.execute(text("SELECT message FROM campaign_events WHERE campaign_id = :c"),
                              {"c": cid}).scalars().all()  # fmt: skip
    assert any("Réglages" in e for e in events)


def test_C182_sms_queued_even_before_the_registry_is_checked(mail_db: Engine) -> None:
    """Le registre est consulté après la campagne : le SMS est revérifié à l'envoi."""
    sms_ready(mail_db)
    cid, kept, _ = _campaign(mail_db)
    queue_campaign_mails(mail_db, BOX, cid, NOW)
    with mail_db.connect() as conn:
        queued = conn.execute(text("SELECT prospect_id FROM sms_queue")).scalars().all()
    assert queued == [kept]
