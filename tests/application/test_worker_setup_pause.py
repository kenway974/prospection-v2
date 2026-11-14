"""Retour du 14/11 : la file s'arrêtait sur « Reliez votre Gmail » alors que Gmail était
relié. C'est la tâche de fond qui envoie : il lui manquait les identifiants Gmail et
l'adresse publique (variables du service worker sur Railway)."""

import random
from datetime import UTC, datetime

from sqlalchemy import Engine

from prospection.application.mail_batch import queue_batch
from prospection.application.mail_queue_run import send_next
from prospection.storage.mail_queue_settings import paused
from tests.application.campaign_helpers import BOX
from tests.application.mail_helpers import BASE, OAUTH, add_audited, google, ready

TUESDAY = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)


def _run(engine: Engine, oauth: object, base: str | None) -> bool:
    return send_next(engine, BOX, google()[0], oauth, base, TUESDAY, "Europe/Paris",  # type: ignore[arg-type]
                     random.Random(0))  # noqa: S311  # fmt: skip


def test_worker_says_which_railway_variables_are_missing(mail_db: Engine) -> None:
    ready(mail_db)
    queue_batch(mail_db, BOX, [add_audited(mail_db)], TUESDAY)
    assert not _run(mail_db, None, BASE)
    with mail_db.connect() as conn:
        reason = paused(conn) or ""
    assert "GMAIL_CLIENT_ID" in reason and "service worker" in reason
    assert not _run(mail_db, OAUTH, None)
    with mail_db.connect() as conn:
        assert "PUBLIC_URL" in (paused(conn) or "")


def test_queue_resumes_by_itself_once_the_worker_is_configured(mail_db: Engine) -> None:
    ready(mail_db)
    queue_batch(mail_db, BOX, [add_audited(mail_db)], TUESDAY)
    _run(mail_db, None, BASE)
    assert _run(mail_db, OAUTH, BASE)  # variables ajoutées : le mail part
    with mail_db.connect() as conn:
        assert paused(conn) is None
