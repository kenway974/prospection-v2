"""C164 : page Stats : envois, conversations, classements par version et profil de lead."""

import html

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.application.call_actions import record_result
from prospection.application.mail_stats_page import stats_screen
from tests.application.campaign_helpers import NOW
from tests.application.mail_helpers import add_audited, ready
from tests.application.test_mail_versions import send_shown
from tests.fake_http import Recorder


def two_sends(engine: Engine) -> None:
    ready(engine)
    first = add_audited(engine)
    send_shown(engine, first)
    record_result(engine, first, "intéressé", NOW)
    send_shown(engine, add_audited(engine, contacts_email="devis@autre.fr"))


def test_C164_totals_and_rankings(mail_db: Engine) -> None:
    two_sends(mail_db)
    screen = stats_screen(mail_db)
    assert (screen.sends, screen.conversations, screen.replies, screen.bounced) == (2, 1, 0, 0)
    sections = dict(screen.sections)
    assert [r.sends for r in sections["Structures"]] == [1, 1]
    assert sections["Structures"][0].conversations == 1  # « détaillée » a mené à l'appel
    assert sections["Métiers"][0].label == "plombier"


def test_C164_page_lists_and_warns_when_too_few(
    web: tuple[TestClient, Recorder],
    mail_db: Engine,
) -> None:
    client, _ = web
    two_sends(mail_db)
    page = html.unescape(client.get("/stats").text)
    assert "Stats des mails d'audit" in page and "2 envois" in page
    assert "pas assez d'envois pour conclure" in page and "Objets" in page
    assert 'href="/stats"' in client.get("/prospects").text


def test_C164_empty_page_says_what_to_do(
    web: tuple[TestClient, Recorder],
    mail_db: Engine,
) -> None:
    client, _ = web
    page = html.unescape(client.get("/stats").text)
    assert "Aucun mail d'audit envoyé pour l'instant" in page
