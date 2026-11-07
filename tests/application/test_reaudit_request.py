"""C156 : « Refaire l'audit » sur la fiche ; la tâche de fond s'en charge, gratuitement."""

import dataclasses

from sqlalchemy import Engine

from prospection.application.prospect_card import card
from prospection.application.site_reaudit import request_reaudit, run_reaudits
from prospection.domain.page_speed import PageSpeed
from prospection.domain.place import Place
from prospection.domain.site_report import SiteReport
from tests.application.campaign_helpers import NOW
from tests.application.mail_helpers import AUDIT, SITE, add_audited

SPEED = PageSpeed(42, 5200, ())
NEW = dataclasses.replace(AUDIT, form_place="sur une page Contact")
PARIS = "Europe/Paris"


def checker(place: Place, keywords: tuple[str, ...]) -> SiteReport:
    return dataclasses.replace(SITE, audit=NEW)


def test_C156_audit_redone_on_request_only_keeping_speed(mail_db: Engine) -> None:
    pid = add_audited(mail_db, dataclasses.replace(SITE, speed=SPEED))
    assert run_reaudits(mail_db, checker, NOW) == 0  # rien de demandé : rien de fait
    request_reaudit(mail_db, pid, NOW)
    assert card(mail_db, pid, NOW, PARIS).reaudit_pending
    assert run_reaudits(mail_db, checker, NOW) == 1
    shown = card(mail_db, pid, NOW, PARIS)
    assert not shown.reaudit_pending
    site = shown.prospect.site
    assert site is not None and site.audit == NEW and site.speed == SPEED
    assert run_reaudits(mail_db, checker, NOW) == 0


def test_C156_without_site_reader_request_waits(mail_db: Engine) -> None:
    pid = add_audited(mail_db)
    request_reaudit(mail_db, pid, NOW)
    assert run_reaudits(mail_db, lambda place, keywords: None, NOW) == 0
    assert card(mail_db, pid, NOW, PARIS).reaudit_pending


def test_C156_crashing_site_does_not_block_the_others(mail_db: Engine) -> None:
    first, second = add_audited(mail_db), add_audited(mail_db)
    request_reaudit(mail_db, first, NOW)
    request_reaudit(mail_db, second, NOW)

    def crash_first(place: Place, keywords: tuple[str, ...]) -> SiteReport:
        if crash_first.calls == 0:  # type: ignore[attr-defined]
            crash_first.calls = 1  # type: ignore[attr-defined]
            raise RuntimeError("page piégée")
        return checker(place, keywords)

    crash_first.calls = 0  # type: ignore[attr-defined]
    assert run_reaudits(mail_db, crash_first, NOW) == 2
    assert not card(mail_db, first, NOW, PARIS).reaudit_pending  # abandonné, l'ancien gardé
    assert not card(mail_db, second, NOW, PARIS).reaudit_pending
