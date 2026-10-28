"""C67 à C75, C32 : envoi des intéressés vers Notion par la tâche de fond (faux Notion)."""

from datetime import timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import store_key
from prospection.application.crm_export import export_report, queue_export, send_pending
from prospection.application.crm_index import refresh_crm_index
from prospection.application.prospect_card import card, prospect_list
from prospection.domain.crm_choice import Crm
from prospection.domain.services import Service
from prospection.storage.app_settings import save_crm
from prospection.storage.exclusions import load_exclusions
from prospection.storage.secret_box import SecretBox
from tests.application.campaign_helpers import BOX, NOW
from tests.application.test_call_tracking import PARIS, add
from tests.fake_http import fake_client
from tests.fake_notion import FakeNotion, _as_read, _text
from tests.storage.test_campaigns import PLACE

DB = "ebbf6ef71a4945bf8575a326c745d824"


def with_notion(engine: Engine, box: SecretBox = BOX) -> None:
    store_key(engine, box, Service.NOTION, "secret_notion", NOW)
    with engine.begin() as conn:
        save_crm(conn, Crm.NOTION, DB, "Prospects v2")


def interested(engine: Engine) -> int:
    [pid] = add(engine, PLACE)
    with engine.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET status = 'intéressé' WHERE id = %s", (pid,))
    return pid


def test_C68_C71_C72_sent_then_exported_with_link(campaign_db: Engine) -> None:
    with_notion(campaign_db)
    pid = interested(campaign_db)
    queue_export(campaign_db, [pid], NOW)
    notion = FakeNotion()
    client, _ = fake_client(notion)
    assert send_pending(campaign_db, BOX, client, NOW) == 1
    [page] = notion.pages.values()
    props = page["properties"]
    assert _text(page, "ID app") == "p1" and props["Statut CRM"]["status"]["name"] == "Nouveau"  # type: ignore[index]
    assert _text(page, "Campagne") == "Test" and "Exporté le" in props  # type: ignore[operator]
    shown = card(campaign_db, pid, NOW, PARIS)
    assert shown.prospect.status == "exporté" and shown.crm_url == "https://notion.so/p1"
    report = export_report(campaign_db)
    assert (report.created, report.updated, report.failed) == (1, 0, [])


def test_C69_C70_sent_again_updates_without_overwriting(campaign_db: Engine) -> None:
    with_notion(campaign_db)
    pid = interested(campaign_db)
    notion = FakeNotion()
    client, _ = fake_client(notion)
    queue_export(campaign_db, [pid], NOW)
    send_pending(campaign_db, BOX, client, NOW)
    page = notion.pages["p1"]
    page["properties"]["Ville"] = {"type": "rich_text", "rich_text": [{"plain_text": "Saisi main"}]}  # type: ignore[index]
    queue_export(campaign_db, [pid], NOW + timedelta(days=1))
    send_pending(campaign_db, BOX, client, NOW + timedelta(days=1))
    assert len(notion.pages) == 1  # pas de doublon
    assert _text(page, "Ville") == "Saisi main"  # saisie manuelle gardée
    assert export_report(campaign_db).updated == 1


def test_C73_notion_down_nothing_lost_retried_later(campaign_db: Engine) -> None:
    with_notion(campaign_db)
    pid = interested(campaign_db)
    notion = FakeNotion()
    notion.answer = httpx.Response(503)
    client, _ = fake_client(notion)
    queue_export(campaign_db, [pid], NOW)
    send_pending(campaign_db, BOX, client, NOW)
    assert prospect_list(campaign_db, None, "", "trouves").rows[0].status == "intéressé"
    notion.answer = None
    assert send_pending(campaign_db, BOX, client, NOW) == 0  # pas avant le délai
    assert send_pending(campaign_db, BOX, client, NOW + timedelta(minutes=10)) == 1
    assert prospect_list(campaign_db, None, "", "trouves").rows[0].status == "exporté"


def test_C74_refusal_reported_with_its_reason(campaign_db: Engine) -> None:
    with_notion(campaign_db)
    pid = interested(campaign_db)
    notion = FakeNotion()
    notion.answer = httpx.Response(400, json={"message": "Score is expected to be number."})
    client, _ = fake_client(notion)
    queue_export(campaign_db, [pid], NOW)
    send_pending(campaign_db, BOX, client, NOW)
    [(name, reason)] = export_report(campaign_db).failed
    assert name == "Atelier" and "Score is expected" in reason


def test_C32_crm_index_excludes_known_prospects(campaign_db: Engine) -> None:
    with_notion(campaign_db)
    notion = FakeNotion()
    notion.pages["x"] = {"id": "x", "url": "u", "properties": _as_read({
        "ID app": {"rich_text": [{"text": {"content": "place-7"}}]},
        "SIREN": {"rich_text": [{"text": {"content": "912345678"}}]},
        "Entreprise": {"title": [{"text": {"content": "Cuisines Hoarau"}}]}})}  # fmt: skip
    client, _ = fake_client(notion)
    assert refresh_crm_index(campaign_db, BOX, client, NOW) == 1
    with campaign_db.connect() as conn:
        exclusions = load_exclusions(conn)
    assert "place-7" in exclusions.crm_ids and "912345678" in exclusions.crm_sirens
    assert "cuisines hoarau" in exclusions.crm_names
