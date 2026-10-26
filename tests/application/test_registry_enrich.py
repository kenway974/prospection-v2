"""C44, C45, C93 : les prospects trouvés sur Google sont rapprochés du registre."""

import dataclasses

import httpx
from sqlalchemy import Engine

from prospection.application.prospect_card import card
from prospection.application.registry_enrich import enrich_new_prospects
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import PARIS, add
from tests.fake_http import fake_client, json_reply
from tests.sources.test_company_registry import page, result
from tests.storage.test_campaigns import PLACE

MARTIN = dataclasses.replace(
    PLACE, name="Cuisines Martin", address="12 rue de la République, 69002 Lyon", country="FR"
)


def run(engine: Engine, handler: object) -> list[httpx.Request]:
    client, recorder = fake_client(handler)  # type: ignore[arg-type]
    enrich_new_prospects(engine, client, NOW, pause=0)
    return recorder.requests


def test_C44_C45_sure_match_adds_the_company(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, MARTIN)
    requests = run(campaign_db, json_reply(200, page(result())))
    assert requests[0].url.params["code_postal"] == "69002"
    shown = card(campaign_db, pid, NOW, PARIS)
    assert ("SIREN", "912 345 678") in shown.company_lines
    assert run(campaign_db, json_reply(200, page(result()))) == []  # déjà fait : rien de plus


def test_C45_unsure_match_flagged_to_confirm(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, dataclasses.replace(MARTIN, address="1 place, 69009 Lyon"))
    run(campaign_db, json_reply(200, page(result())))
    shown = card(campaign_db, pid, NOW, PARIS)
    assert "Entreprise à confirmer" in shown.prospect.to_check and shown.company_lines == []


def test_registry_down_retried_later(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, MARTIN)
    run(campaign_db, json_reply(503, {}))
    assert card(campaign_db, pid, NOW, PARIS).company_lines == []
    run(campaign_db, json_reply(200, page(result())))
    assert card(campaign_db, pid, NOW, PARIS).company_lines != []


def test_C93_non_diffusible_shows_nothing_personal(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, MARTIN)
    run(campaign_db, json_reply(200, page(result(statut_diffusion="P"))))
    lines = card(campaign_db, pid, NOW, PARIS).company_lines
    assert lines == [("Registre", "Données non diffusées à la demande de l'entreprise.")]


def test_outside_france_not_looked_up(campaign_db: Engine) -> None:
    add(campaign_db, dataclasses.replace(MARTIN, country="BE", address="Rue 1, 4000 Liège"))
    assert run(campaign_db, json_reply(200, page(result()))) == []
