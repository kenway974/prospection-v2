"""C176, C177 : le SMS sur l'écran de l'envoi groupé et dans la file : mobile français,
jamais vers un non diffusible ni après un STOP, une seule fois ; seul quand il n'y a pas
d'adresse mail."""

from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.application.mail_batch import batch_preview, queue_batch
from prospection.domain.services import Service
from prospection.domain.sms_target import phone_fingerprint
from prospection.storage.mail_queue import pending_ids
from prospection.storage.sms_queue_store import add_stops, record_sms
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import add_audited, ready

MOBILE = "+33612345678"  # numéro de la fiche Google d'exemple


def sms_ready(engine: Engine) -> None:
    ready(engine)
    store_key(engine, BOX, Service.BREVO, "cle-brevo", NOW)
    with engine.begin() as conn:
        conn.exec_driver_sql("UPDATE sms_settings SET enabled = true")
        conn.exec_driver_sql("UPDATE mail_settings SET phone = '06 81 78 73 25'")


def _sms(engine: Engine, ids: list[int]) -> dict[int, str | None]:
    return {r.prospect_id: r.sms_reason for r in batch_preview(engine, BOX, ids).rows}


def test_C177_sms_leaves_with_the_mail_when_enabled(mail_db: Engine) -> None:
    ready(mail_db)
    pid = add_audited(mail_db, contacts_email="a@martin.fr")
    assert _sms(mail_db, [pid])[pid] == "SMS désactivés (Réglages → SMS)"
    sms_ready(mail_db)
    assert _sms(mail_db, [pid])[pid] is None


def test_C176_never_to_landline_non_diffusible_stop_or_twice(mail_db: Engine) -> None:
    sms_ready(mail_db)
    landline, private, stopped, twice = (
        add_audited(mail_db, contacts_email=f"{n}@martin.fr") for n in "abcd"
    )
    with mail_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET data_json = jsonb_set(data_json, '{phone}', "
                             "'\"04 72 00 00 00\"') WHERE id = %(p)s", {"p": landline})  # fmt: skip
        conn.exec_driver_sql("UPDATE prospects SET registry_status = 'non diffusible' "
                             "WHERE id = %(p)s", {"p": private})  # fmt: skip
        add_stops(conn, [phone_fingerprint(MOBILE, BOX.pepper)], NOW)
    reasons = _sms(mail_db, [landline, private, stopped])
    assert reasons[landline] == "pas de mobile"
    assert reasons[private] == "entrepreneur non diffusible"
    assert reasons[stopped] == "a répondu STOP"
    with mail_db.begin() as conn:
        conn.exec_driver_sql("DELETE FROM sms_optouts")
        record_sms(conn, twice, phone_fingerprint(MOBILE, BOX.pepper), "mail", NOW)
    assert _sms(mail_db, [twice])[twice] == "SMS déjà envoyé"


def test_C177_without_email_the_sms_leaves_alone(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = add_audited(mail_db)
    with mail_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET site_json = jsonb_set(site_json, "
                             "'{contacts,emails}', '[]') WHERE id = %(p)s", {"p": pid})  # fmt: skip
    row = batch_preview(mail_db, BOX, [pid]).rows[0]
    assert row.reason == "pas d'email valide" and row.sms_reason is None
    assert queue_batch(mail_db, BOX, [pid], NOW) == 1
    with mail_db.connect() as conn:
        assert pending_ids(conn) == []
        after = conn.exec_driver_sql("SELECT after_mail FROM sms_queue").scalar_one()
    assert after is False


def test_C177_sms_alone_is_never_queued_twice(mail_db: Engine) -> None:
    sms_ready(mail_db)
    pid = add_audited(mail_db)
    with mail_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET site_json = jsonb_set(site_json, "
                             "'{contacts,emails}', '[]') WHERE id = %(p)s", {"p": pid})  # fmt: skip
    assert queue_batch(mail_db, BOX, [pid], NOW) == 1
    assert queue_batch(mail_db, BOX, [pid], NOW) == 0
