"""C157 : « Mail refusé » : refus noté, nouvel envoi possible vers une autre adresse."""

import dataclasses

import pytest
from sqlalchemy import Engine

from prospection.application.audit_mail import MailBlocked
from prospection.application.mail_bounce import mark_bounced
from prospection.application.prospect_card import card
from prospection.domain.site_contacts import Contacts
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import SITE, add_audited, ready
from tests.application.test_audit_mail import PARIS, screen, send

TWO = dataclasses.replace(SITE, contacts=Contacts(("contact@martin.fr", "devis@martin.fr"), (), ()))


def test_C157_bounce_noted_then_another_address_can_be_used(mail_db: Engine) -> None:
    pid = add_audited(mail_db, TWO)
    ready(mail_db)
    send(mail_db, pid)
    mark_bounced(mail_db, pid, NOW, BOX.pepper)
    shown = card(mail_db, pid, NOW, PARIS)
    assert shown.mail_sent_on is None
    assert shown.notes[0].text.startswith("Mail d'audit refusé par le serveur de contact@martin.fr")
    assert "ne reçoit pas les mails" in shown.notes[0].text
    assert screen(mail_db, pid).recipients == ["devis@martin.fr"]  # jamais la même adresse
    send(mail_db, pid, "devis@martin.fr")
    assert card(mail_db, pid, NOW, PARIS).mail_sent_on == NOW


def test_C157_nothing_to_mark_without_a_sent_mail(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    with pytest.raises(MailBlocked, match="Aucun mail"):
        mark_bounced(mail_db, pid, NOW, BOX.pepper)
