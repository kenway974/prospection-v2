"""C76, C77, C78, C108 : alertes, rappels, programmations, mise à jour (écrans)."""

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from prospection.storage.alerts import add_alert
from prospection.storage.campaigns import set_status
from prospection.storage.templates import save_template
from tests.application.campaign_helpers import NOW, request
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE
from tests.ui.test_call_screens import client, text
from tests.ui.test_search_form import ORIGIN

__all__ = ["client"]  # fixture partagée


def test_C108_alert_on_today_screen_until_seen(client: TestClient, campaign_db: Engine) -> None:
    with campaign_db.begin() as conn:
        add_alert(conn, "relance:1", "relance", "Rappeler · <b>Atelier</b> · 14:30", "/prospects/1",
                  NOW)  # fmt: skip
    page = client.get("/").text
    assert "&lt;b&gt;Atelier&lt;/b&gt;" in page and "<b>Atelier" not in page  # texte échappé
    client.post("/alertes/1/vu", headers=ORIGIN)
    assert "Atelier" not in text(client.get("/"))


def test_C108_reminder_settings(client: TestClient) -> None:
    assert 'value="15"' in text(client.get("/reglages/rappels"))
    ok = client.post("/reglages/rappels", data={"minutes": "30", "heure": "7"}, headers=ORIGIN,
                     follow_redirects=False)  # fmt: skip
    assert ok.status_code == 303 and 'value="30"' in text(client.get("/reglages/rappels"))
    bad = client.post("/reglages/rappels", data={"minutes": "x", "heure": "7"}, headers=ORIGIN)
    assert bad.status_code == 400 and "entre 0 et 240" in text(bad)


def test_C77_schedule_a_template_every_week(client: TestClient, campaign_db: Engine) -> None:
    assert "Enregistrez d'abord un modèle" in text(client.get("/programmes"))
    with campaign_db.begin() as conn:
        save_template(conn, "Créations 69", request())
    form = {"modele": "Créations 69", "jour": "0", "heure": "7"}
    client.post("/programmes", data=form, headers=ORIGIN)
    page = text(client.get("/programmes"))
    assert "Chaque lundi à 7 h" in page and "26/10" in page
    bad = client.post("/programmes", data={**form, "heure": "25"}, headers=ORIGIN)
    assert bad.status_code == 400
    client.post("/programmes/1/supprimer", headers=ORIGIN)
    assert "Chaque lundi" not in text(client.get("/programmes"))


def test_C76_update_offered_on_a_finished_campaign(client: TestClient, campaign_db: Engine) -> None:
    add(campaign_db, PLACE)
    assert "Mettre à jour" not in text(client.get("/campagnes/1"))  # pas encore finie
    with campaign_db.begin() as conn:
        set_status(conn, 1, "done", NOW, "Objectif atteint : 1 prospect qualifié.")
    assert "Dans le quota gratuit" in text(client.get("/campagnes/1"))
    client.post("/campagnes/1/mettre-a-jour", headers=ORIGIN)
    assert "Mise à jour en cours : 1 fiches restantes" in text(client.get("/campagnes/1"))
