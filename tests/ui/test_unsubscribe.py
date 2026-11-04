"""C148 : désinscription publique, confirmée en un clic (ou en un clic depuis Gmail)."""

import html

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.application.audit_mail import mail_screen
from prospection.storage.privacy import delete_prospects
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import BASE, OAUTH, add_audited, google, ready
from tests.application.test_audit_mail import send


def token_of(engine: Engine) -> str:
    with engine.connect() as conn:
        return str(conn.exec_driver_sql("SELECT token FROM mail_sends").scalar_one())


def recipients(engine: Engine, pid: int) -> list[str]:
    return mail_screen(engine, BOX, google()[0], OAUTH, BASE, pid, NOW).recipients


def test_C148_public_page_confirms_then_address_never_used_again(
    client: TestClient, mail_db: Engine
) -> None:
    pid = add_audited(mail_db)
    ready(mail_db)
    send(mail_db, pid)
    token = token_of(mail_db)
    client.cookies.clear()  # page publique : aucune connexion
    page = client.get(f"/desinscription/{token}")
    assert page.status_code == 200 and "Confirmer" in html.unescape(page.text)
    assert recipients(mail_db, add_audited(mail_db)) == ["contact@martin.fr"]  # pas encore
    done = client.post(f"/desinscription/{token}")  # sans origine : comme Gmail en un clic
    assert done.status_code == 200 and "ne recevrez plus" in html.unescape(done.text)
    assert recipients(mail_db, add_audited(mail_db)) == []


def test_C148_link_still_works_after_the_prospect_is_deleted(
    client: TestClient, mail_db: Engine
) -> None:
    pid = add_audited(mail_db)
    ready(mail_db)
    send(mail_db, pid)
    with mail_db.begin() as conn:
        delete_prospects(conn, [pid])
    assert client.post(f"/desinscription/{token_of(mail_db)}").status_code == 200
    assert recipients(mail_db, add_audited(mail_db)) == []


def test_C148_unknown_link_said_plainly(client: TestClient) -> None:
    response = client.post("/desinscription/inconnu")
    assert response.status_code == 404 and "inconnu" in html.unescape(response.text)
