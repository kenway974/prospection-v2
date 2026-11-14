"""C168 : « Envoyer le mail d'audit » sur la sélection de la page Prospects."""

import html

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.storage.mail_queue import pending_ids
from tests.application.mail_helpers import add_audited, ready
from tests.fake_http import Recorder
from tests.ui.test_mail_screens import web  # noqa: F401 (fixture)
from tests.ui.test_settings_keys import ORIGIN


def test_C168_button_next_to_delete_then_confirmation_then_queue(
    web: tuple[TestClient, Recorder],  # noqa: F811
    mail_db: Engine,
) -> None:
    client, recorder = web
    ready(mail_db)
    ok = add_audited(mail_db, contacts_email="ok@martin.fr")
    none = add_audited(mail_db, site=None)
    assert 'formaction="/prospects/selection/mail"' in client.get("/prospects").text
    page = html.unescape(
        client.post("/prospects/selection/mail", data={"id": [ok, none]}, headers=ORIGIN).text
    )
    assert "1 mail partira" in page and "ok@martin.fr" in page and "30 par jour" in page
    assert "pas encore d'audit" in page and "SMS : SMS désactivés" in page
    done = client.post("/prospects/selection/mail/envoyer", data={"id": [ok, none]},
                       headers=ORIGIN, follow_redirects=False)  # fmt: skip
    assert done.status_code == 303
    with mail_db.connect() as conn:
        assert pending_ids(conn) == [ok]
    assert recorder.requests == []  # rien ne part depuis l'interface
    assert "1 mail d'audit en file" in html.unescape(client.get(done.headers["location"]).text)


def test_C168_buttons_have_the_app_style(
    web: tuple[TestClient, Recorder],  # noqa: F811
    mail_db: Engine,
) -> None:
    """Retour du 11/11 : boutons bruts du navigateur sur la page Prospects."""
    add_audited(mail_db)
    page = web[0].get("/prospects").text
    assert 'formaction="/prospects/selection/mail" class="button-primary"' in page


def test_C186_summary_on_top_of_the_confirmation(
    web: tuple[TestClient, Recorder],  # noqa: F811
    mail_db: Engine,
) -> None:
    ready(mail_db)
    ids = [add_audited(mail_db, site=None) for _ in range(2)]
    page = html.unescape(web[0].post("/prospects/selection/mail", data={"id": ids},
                                     headers=ORIGIN).text)  # fmt: skip
    assert "Écartés : 2 pas encore d'audit" in page
    assert page.index("Écartés : 2") < page.index("Envoi sans relecture")
