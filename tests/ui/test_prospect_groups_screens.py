"""C183, C184, C185 : campagnes repliables avec leur « Tout cocher », badge et filtre du
mail d'audit, nouvel audit des prospects cochés."""

import html

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from tests.application.mail_helpers import add_audited, ready
from tests.application.test_audit_mail import send
from tests.fake_http import Recorder
from tests.ui.test_mail_screens import web  # noqa: F401 (fixture)
from tests.ui.test_settings_keys import ORIGIN

Web = tuple[TestClient, Recorder]


def test_C183_campaigns_collapsed_with_their_own_check_all(web: Web, mail_db: Engine) -> None:  # noqa: F811
    add_audited(mail_db)
    page = web[0].get("/prospects").text
    assert '<details class="campaign">' in page and "<summary" in page  # replié par défaut
    assert 'class="cocher-campagne"' in page and "les 1 prospects" not in page
    assert "cocher le prospect de la campagne" in html.unescape(page)
    assert page.index('class="cocher-campagne"') < page.index("<summary")  # hors du titre


def test_C184_badge_and_filter_for_mailed_prospects(web: Web, mail_db: Engine) -> None:  # noqa: F811
    client, _ = web
    ready(mail_db)
    sent = add_audited(mail_db, contacts_email="a@martin.fr")
    send(mail_db, sent, to="a@martin.fr")
    add_audited(mail_db, contacts_email="b@martin.fr")
    page = html.unescape(client.get("/prospects").text)
    assert 'class="badge badge-envoye"' in page and "Mail envoyé le 25/10" in page
    assert "Déjà contacté · 1" in page and "Pas encore contacté · 1" in page
    filtered = html.unescape(client.get("/prospects?contact=non").text)
    assert "Mail envoyé le" not in filtered.split("Pas encore contacté · 1")[1]


def test_C185_reaudit_the_checked_prospects(web: Web, mail_db: Engine) -> None:  # noqa: F811
    client, _ = web
    pid = add_audited(mail_db)
    assert 'formaction="/prospects/selection/audit"' in client.get("/prospects").text
    done = client.post("/prospects/selection/audit", data={"id": [pid]}, headers=ORIGIN,
                       follow_redirects=False)  # fmt: skip
    assert done.status_code == 303
    with mail_db.connect() as conn:
        asked = conn.exec_driver_sql(
            "SELECT reaudit_requested_at FROM prospects WHERE id = %(p)s", {"p": pid}
        ).scalar()
    assert asked is not None
