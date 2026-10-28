"""C99 : vérification hebdomadaire des vraies API (faux services ici, aucun réseau)."""

from datetime import timedelta

import httpx
from sqlalchemy import Engine

from prospection.application.api_watch import weekly_api_check
from prospection.storage.alerts import unseen_alerts
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place
from tests.fake_http import fake_client


def healthy(request: httpx.Request) -> httpx.Response:
    if request.url.host == "recherche-entreprises.api.gouv.fr":
        result = {"siren": "441639465", "nom_complet": "RENAULT", "siege": {}}
        return httpx.Response(200, json={"results": [result]})
    return httpx.Response(200, json={"places": [api_place(1)]})


def test_C99_weekly_and_silent_when_all_is_well(campaign_db: Engine) -> None:
    client, seen = fake_client(healthy)
    assert weekly_api_check(campaign_db, BOX, client, PRICING, NOW)
    assert not weekly_api_check(campaign_db, BOX, client, PRICING, NOW + timedelta(days=6))
    with campaign_db.connect() as conn:
        assert unseen_alerts(conn) == []
    assert {r.url.host for r in seen.requests} == {
        "places.googleapis.com",
        "recherche-entreprises.api.gouv.fr",
    }
    assert weekly_api_check(campaign_db, BOX, client, PRICING, NOW + timedelta(days=7))


def test_C99_alert_when_a_format_changes(campaign_db: Engine) -> None:
    def changed(request: httpx.Request) -> httpx.Response:
        if request.url.host == "recherche-entreprises.api.gouv.fr":
            return httpx.Response(200, json={"résultats": []})
        if request.headers.get("X-Goog-FieldMask") == "places.id":  # test de la clé : accepté
            return httpx.Response(200, json={"places": [{"id": "x"}]})
        return httpx.Response(200, json={"places": [{"id": 1, "displayName": "?"}]})

    client, _ = fake_client(changed)
    weekly_api_check(campaign_db, BOX, client, PRICING, NOW)
    with campaign_db.connect() as conn:
        messages = sorted(a.message for a in unseen_alerts(conn))
    assert messages == [
        "Vérification hebdomadaire · Google Maps : aucun établissement lisible (format changé ?)",
        "Vérification hebdomadaire · Registre des entreprises : aucun résultat lisible",
    ]


def test_C99_refused_key_reported(campaign_db: Engine) -> None:
    client, _ = fake_client(lambda r: httpx.Response(403, json={"error": {}}))
    weekly_api_check(campaign_db, BOX, client, PRICING, NOW)
    with campaign_db.connect() as conn:
        messages = [a.message for a in unseen_alerts(conn)]
    assert any(
        m.startswith("Vérification hebdomadaire · Google Maps : Google refuse") for m in messages
    )


def test_C99_passing_outage_retried_then_reported_if_it_lasts(campaign_db: Engine) -> None:
    client, seen = fake_client(lambda r: httpx.Response(503, json={}))
    weekly_api_check(campaign_db, BOX, fake_client(healthy)[0], PRICING, NOW)  # semaine 1 : ok
    later = NOW + timedelta(days=7)
    with campaign_db.begin() as conn:  # clé Google acceptée, le reste en panne
        conn.exec_driver_sql("DELETE FROM api_keys")
    assert weekly_api_check(campaign_db, BOX, client, PRICING, later)
    with campaign_db.connect() as conn:
        assert unseen_alerts(conn) == []  # une panne passagère ne dit rien…
    assert not weekly_api_check(campaign_db, BOX, client, PRICING, later + timedelta(minutes=30))
    assert weekly_api_check(campaign_db, BOX, client, PRICING, later + timedelta(hours=1))
    with campaign_db.connect() as conn:
        [alert] = unseen_alerts(conn)  # … mais deux de suite, si
    assert "deux fois de suite" in alert.message and seen.requests


def test_C99_refused_google_key_not_charged_again(campaign_db: Engine) -> None:
    client, seen = fake_client(lambda r: httpx.Response(403, json={"error": {}}))
    weekly_api_check(campaign_db, BOX, client, PRICING, NOW)
    google = [r for r in seen.requests if r.url.host == "places.googleapis.com"]
    assert len(google) == 1  # le test de la clé seulement, pas de page payée
