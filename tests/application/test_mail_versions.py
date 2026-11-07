"""C162 : versions tournantes ; chaque envoi garde versions, modification, points et profil."""

from sqlalchemy import Engine

from prospection.application.audit_mail import send_audit_mail
from prospection.domain.audit_mail_rules import load_mail_rules
from prospection.storage.mail_send_log import all_sends
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import BASE, OAUTH, add_audited, google, ready
from tests.application.test_audit_mail import PARIS, screen


def send_shown(engine: Engine, pid: int, edit: bool = False) -> None:
    shown = screen(engine, pid)
    assert shown.draft is not None
    body = shown.draft.body + ("\n\nPS : à bientôt" if edit else "")
    send_audit_mail(engine, BOX, google()[0], OAUTH, BASE, pid, shown.recipients[0],
                    shown.draft.subject, body, NOW, PARIS, shown.versions)  # fmt: skip


def test_C162_versions_rotate_and_each_send_is_recorded(mail_db: Engine) -> None:
    ready(mail_db)
    objets = load_mail_rules().objets
    first = screen(mail_db, add_audited(mail_db))
    assert first.versions.subject == objets[0] and first.versions.structure == "détaillée"
    send_shown(mail_db, first.prospect_id)
    second = screen(mail_db, add_audited(mail_db, contacts_email="devis@autre.fr"))
    assert second.versions.subject == objets[1] and second.versions.structure == "courte"
    send_shown(mail_db, second.prospect_id, edit=True)
    with mail_db.connect() as conn:
        sends = all_sends(conn)
    assert [s.subject_version for s in sends] == [objets[0], objets[1]]
    assert [s.edited for s in sends] == [False, True]
    assert sends[0].thread_id == "fil-1" and sends[0].points
    assert sends[0].profile["site"] == "avec site" and sends[0].profile["métier"] == "plombier"


def test_C162_no_site_prospect_never_gets_a_site_subject(mail_db: Engine) -> None:
    from prospection.domain.site_report import SiteReport

    ready(mail_db)
    no_site = SiteReport("aucun", contacts=None)
    pid = add_audited(mail_db, no_site)
    with mail_db.begin() as conn:
        conn.exec_driver_sql(
            "UPDATE prospects SET contact_email = 'patron@martin.fr' WHERE id = %(id)s", {"id": pid}
        )
    shown = screen(mail_db, pid)
    assert shown.draft is not None and "site" not in shown.draft.subject.lower()
    assert (
        shown.versions is not None and shown.versions.subject in load_mail_rules().objets_sans_site
    )
