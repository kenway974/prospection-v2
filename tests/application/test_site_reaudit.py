"""C152 : les sites audités avant la nouvelle détection sont réaudités, une seule fois."""

import dataclasses

from sqlalchemy import Engine

from prospection.application.site_reaudit import reaudit_sites
from prospection.domain.page_speed import PageSpeed
from prospection.domain.place import Place
from prospection.domain.site_report import SiteReport
from prospection.storage.prospect_list import load_prospect
from tests.application.campaign_helpers import NOW
from tests.application.mail_helpers import AUDIT, SITE, add_audited

OLD = dataclasses.replace(AUDIT, problems=("Pas de formulaire de contact",), codes=("no_form",),
                          form_place=None)  # fmt: skip
SPEED = PageSpeed(42, 5200, ())
NEW = dataclasses.replace(AUDIT, form_place="sur une page Contact")


def checker(calls: list[tuple[str, ...]]):  # type: ignore[no-untyped-def]
    def check(place: Place, keywords: tuple[str, ...]) -> SiteReport:
        calls.append(keywords)
        return dataclasses.replace(SITE, audit=NEW)

    return check


def site_of(engine: Engine, pid: int) -> SiteReport:
    with engine.connect() as conn:
        row = load_prospect(conn, pid)
    assert row is not None and row.site is not None
    return row.site


def test_C152_old_audit_redone_once_keeping_speed(mail_db: Engine) -> None:
    pid = add_audited(mail_db, dataclasses.replace(SITE, audit=OLD, speed=SPEED))
    calls: list[tuple[str, ...]] = []
    assert reaudit_sites(mail_db, checker(calls), NOW) == 1
    site = site_of(mail_db, pid)
    assert site.audit is not None and site.audit.form_place == "sur une page Contact"
    assert site.speed == SPEED and calls == [("plombier",)]
    assert reaudit_sites(mail_db, checker(calls), NOW) == 0  # déjà fait


def test_C152_recent_audit_left_alone(mail_db: Engine) -> None:
    add_audited(mail_db)
    calls: list[tuple[str, ...]] = []
    assert reaudit_sites(mail_db, checker(calls), NOW) == 0 and calls == []


def test_C152_no_site_reader_nothing_changes(mail_db: Engine) -> None:
    pid = add_audited(mail_db, dataclasses.replace(SITE, audit=OLD))
    assert reaudit_sites(mail_db, lambda place, keywords: None, NOW) == 0
    assert site_of(mail_db, pid).audit == OLD


def test_C152_site_that_crashes_is_marked_unverified_never_retried(mail_db: Engine) -> None:
    pid = add_audited(mail_db, dataclasses.replace(SITE, audit=OLD))

    def crash(place: Place, keywords: tuple[str, ...]) -> SiteReport:
        raise RuntimeError("page piégée")

    assert reaudit_sites(mail_db, crash, NOW) == 1
    audit = site_of(mail_db, pid).audit
    assert audit is not None and audit.form_place == "non vérifié"
    assert reaudit_sites(mail_db, crash, NOW) == 0
