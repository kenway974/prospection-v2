"""C156, C157 : boutons « Refaire l'audit » et « Mail refusé » sur la fiche."""

import html

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.application.prospect_card import card
from tests.application.campaign_helpers import NOW
from tests.application.mail_helpers import add_audited, ready
from tests.application.test_audit_mail import PARIS, send
from tests.fake_http import Recorder
from tests.ui.test_mail_screens import web  # noqa: F401 (client avec faux Google)
from tests.ui.test_settings_keys import ORIGIN


def test_C156_reaudit_button_queues_the_audit(web: tuple[TestClient, Recorder],  # noqa: F811
                                               mail_db: Engine) -> None:  # fmt: skip
    client, _ = web
    pid = add_audited(mail_db)
    assert f'action="/prospects/{pid}/audit"' in client.get(f"/prospects/{pid}").text
    response = client.post(f"/prospects/{pid}/audit", headers=ORIGIN, follow_redirects=False)
    assert response.status_code == 303
    page = html.unescape(client.get(f"/prospects/{pid}").text)
    assert "Nouvel audit demandé" in page
    assert card(mail_db, pid, NOW, PARIS).reaudit_pending


def test_C157_bounce_button_after_a_sent_mail(web: tuple[TestClient, Recorder],  # noqa: F811
                                              mail_db: Engine) -> None:  # fmt: skip
    client, _ = web
    pid = add_audited(mail_db)
    ready(mail_db)
    send(mail_db, pid)
    assert f'action="/prospects/{pid}/mail/refuse"' in client.get(f"/prospects/{pid}").text
    client.post(f"/prospects/{pid}/mail/refuse", headers=ORIGIN)
    page = html.unescape(client.get(f"/prospects/{pid}").text)
    assert "Mail d'audit envoyé le" not in page and "refusé par le serveur" in page
