"""C67 à C75 : cas difficiles de l'envoi vers Notion (relecture du lot 7)."""

import threading
from datetime import timedelta

import httpx
from sqlalchemy import Engine

from prospection.application import crm_export
from prospection.application.crm_export import export_report, queue_export, send_pending
from prospection.crm import notion_pages
from tests.application.campaign_helpers import BOX, NOW
from tests.application.test_crm_export import interested, with_notion
from tests.fake_http import fake_client
from tests.fake_notion import FakeNotion, _text


def setup(engine: Engine) -> tuple[int, FakeNotion, httpx.Client]:
    with_notion(engine)
    pid = interested(engine)
    notion = FakeNotion()
    client, _ = fake_client(notion)
    crm_export.reset_pause()
    return pid, notion, client


def test_C67_no_longer_interested_never_sent(campaign_db: Engine) -> None:
    pid, notion, client = setup(campaign_db)
    queue_export(campaign_db, [pid], NOW)
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospects SET status = 'pas intéressé'")
    send_pending(campaign_db, BOX, client, NOW)
    assert notion.calls == [] and export_report(campaign_db).failed[0][1] == "N'est plus intéressé"


def test_C69_two_workers_never_create_twice(campaign_db: Engine) -> None:
    pid, notion, _ = setup(campaign_db)
    queue_export(campaign_db, [pid], NOW)

    def slow(request: httpx.Request) -> httpx.Response:
        threading.Event().wait(0.2)
        return notion(request)

    workers = [threading.Thread(target=send_pending, args=(campaign_db, BOX, fake_client(slow)[0],
                                                           NOW)) for _ in range(2)]  # fmt: skip
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    assert len(notion.pages) == 1


def test_C70_C71_app_columns_kept_up_to_date_and_cleared(campaign_db: Engine) -> None:
    """Réponse perdue puis nouvel export : les colonnes de l'app restent à jour ; une valeur
    devenue vide (action faite) est effacée."""
    pid, notion, client = setup(campaign_db)
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("INSERT INTO prospect_actions (prospect_id, kind, due_date, "
                             "created_at) VALUES (%s, 'Rappeler', '2026-11-02', %s)",
                             (pid, NOW))  # fmt: skip
    lost = {"done": False}

    def answer_lost_once(request: httpx.Request) -> httpx.Response:
        reply = notion(request)  # la page est bien créée dans Notion…
        if request.method == "POST" and request.url.path == "/v1/pages" and not lost["done"]:
            lost["done"] = True
            raise httpx.ReadTimeout("réponse perdue", request=request)  # … mais on ne le sait pas
        return reply

    flaky, _ = fake_client(answer_lost_once)
    queue_export(campaign_db, [pid], NOW)
    send_pending(campaign_db, BOX, flaky, NOW)
    crm_export.reset_pause()
    send_pending(campaign_db, BOX, flaky, NOW + timedelta(minutes=2))  # nouvel essai
    assert len(notion.pages) == 1
    with campaign_db.begin() as conn:
        conn.exec_driver_sql("UPDATE prospect_actions SET done_at = now()")
    later = NOW + timedelta(days=3)
    queue_export(campaign_db, [pid], later)
    send_pending(campaign_db, BOX, client, later)
    props = notion.pages["p1"]["properties"]
    assert props["Exporté le"]["date"]["start"] == "2026-10-28"  # type: ignore[index]
    assert props["Prochaine action"]["rich_text"] == []  # type: ignore[index]
    assert props["Date action"]["date"] is None  # type: ignore[index]


def test_C75_notion_pace_and_retry_after_respected(campaign_db: Engine) -> None:
    pid, notion, client = setup(campaign_db)
    queue_export(campaign_db, [pid], NOW)
    notion.answer = httpx.Response(429, headers={"Retry-After": "120"})
    send_pending(campaign_db, BOX, client, NOW)
    notion.answer = None
    calls = len(notion.calls)
    send_pending(campaign_db, BOX, client, NOW + timedelta(seconds=60))
    assert len(notion.calls) == calls  # pas avant le Retry-After, même pour les autres
    send_pending(campaign_db, BOX, client, NOW + timedelta(minutes=10))
    assert _text(notion.pages["p1"], "ID app") == "p1"
    assert notion_pages.MIN_INTERVAL >= 0.33  # 3 requêtes par seconde au plus


def test_C74_global_refusal_stops_and_keeps_the_queue(campaign_db: Engine) -> None:
    pid, notion, client = setup(campaign_db)
    queue_export(campaign_db, [pid], NOW)
    notion.answer = httpx.Response(401, json={"message": "API token is invalid."})
    send_pending(campaign_db, BOX, client, NOW)
    report = export_report(campaign_db)
    assert report.waiting == 1 and report.failed == []
    assert "Jeton refusé" in (report.problem or "")
