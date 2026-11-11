"""C184 : sur la page Prospects, on voit d'un coup d'œil qui a déjà reçu le mail d'audit,
et un filtre montre « Mail envoyé » ou « Pas encore contacté »."""

from sqlalchemy import Engine

from prospection.application.mail_batch import queue_batch
from prospection.application.mail_bounce import mark_bounced
from prospection.application.prospect_listing import prospect_list
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import add_audited, ready
from tests.application.test_audit_mail import send


def test_C184_each_prospect_says_where_its_mail_stands(mail_db: Engine) -> None:
    ready(mail_db)
    sent = add_audited(mail_db, contacts_email="a@martin.fr")
    send(mail_db, sent, to="a@martin.fr")
    bounced = add_audited(mail_db, contacts_email="b@martin.fr")
    send(mail_db, bounced, to="b@martin.fr")
    mark_bounced(mail_db, bounced, NOW, BOX.pepper)
    queued = add_audited(mail_db, contacts_email="c@martin.fr")
    queue_batch(mail_db, BOX, [queued], NOW)
    fresh = add_audited(mail_db, contacts_email="d@martin.fr")
    marks = prospect_list(mail_db, None, "", "trouves", NOW).contacted
    assert marks[sent] == ("envoye", "Mail envoyé le 25/10")
    assert marks[bounced] == ("refuse", "Mail refusé le 25/10")
    assert marks[queued] == ("file", "En file d'envoi")
    assert fresh not in marks


def test_C184_filter_mailed_or_not_yet_contacted(mail_db: Engine) -> None:
    ready(mail_db)
    sent = add_audited(mail_db, contacts_email="a@martin.fr")
    send(mail_db, sent, to="a@martin.fr")
    fresh = add_audited(mail_db, contacts_email="d@martin.fr")
    mailed = prospect_list(mail_db, None, "", "trouves", NOW, contact="envoye")
    assert [r.id for r in mailed.rows] == [sent]
    untouched = prospect_list(mail_db, None, "", "trouves", NOW, contact="non")
    assert [r.id for r in untouched.rows] == [fresh]
    assert prospect_list(mail_db, None, "", "trouves", NOW).contact_counts == {
        "envoye": 1,
        "non": 1,
    }


def test_C184_call_session_follows_the_filter(mail_db: Engine) -> None:
    from prospection.application.prospect_listing import start_session

    ready(mail_db)
    sent = add_audited(mail_db, contacts_email="a@martin.fr")
    send(mail_db, sent, to="a@martin.fr")
    fresh = add_audited(mail_db, contacts_email="d@martin.fr")
    assert start_session(mail_db, None, "", "trouves", NOW, contact="non") == fresh
