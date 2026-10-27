"""C44, C45, C93 : les prospects trouvés sur Google sont rapprochés du registre."""

import dataclasses

import httpx
from sqlalchemy import Engine, select

from prospection.application.prospect_card import card, prospect_list
from prospection.application.registry_enrich import enrich_new_prospects
from prospection.storage.prospect_list import ProspectRow
from prospection.storage.schema_campaigns import prospects
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import PARIS, add
from tests.fake_http import fake_client, json_reply
from tests.sources.test_company_registry import page, result
from tests.storage.test_campaigns import PLACE

MARTIN = dataclasses.replace(
    PLACE, name="Cuisines Martin", address="12 rue de la République, 69002 Lyon", country="FR"
)


def rows(engine: Engine) -> list[ProspectRow]:
    return prospect_list(engine, None, "", "trouves").rows


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
    assert "Entreprise à confirmer" in shown.prospect.to_check
    assert "à confirmer" in shown.company_lines[0][1]


def test_registry_down_retried_later(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, MARTIN)
    run(campaign_db, json_reply(503, {}))
    waiting = [("Registre", "Pas encore rapprochée du registre des entreprises.")]
    assert card(campaign_db, pid, NOW, PARIS).company_lines == waiting
    run(campaign_db, json_reply(200, page(result())))
    assert ("SIREN", "912 345 678") in card(campaign_db, pid, NOW, PARIS).company_lines


def test_C93_non_diffusible_shows_nothing_personal(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, MARTIN)
    run(campaign_db, json_reply(200, page(result(statut_diffusion="P"))))
    lines = card(campaign_db, pid, NOW, PARIS).company_lines
    assert lines == [("Registre", "Données non diffusées à la demande de l'entreprise.")]


def test_outside_france_not_looked_up(campaign_db: Engine) -> None:
    add(campaign_db, dataclasses.replace(MARTIN, country="BE", address="Rue 1, 4000 Liège"))
    assert run(campaign_db, json_reply(200, page(result()))) == []


def test_refused_search_does_not_block_the_others(campaign_db: Engine) -> None:
    other = dataclasses.replace(MARTIN, place_id="autre", name="Cuisines Martin Lyon")
    add(campaign_db, MARTIN, other)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["q"] == "Cuisines Martin":  # refusée pour de bon (4xx)
            return httpx.Response(400, json={})
        return httpx.Response(200, json=page(result()))

    run(campaign_db, handler)
    cards = {
        c.prospect.data["name"]: c
        for c in (card(campaign_db, r.id, NOW, PARIS) for r in rows(campaign_db))
    }
    assert "Entreprise à confirmer" in cards["Cuisines Martin"].prospect.to_check
    assert ("SIREN", "912 345 678") in cards["Cuisines Martin Lyon"].company_lines


def test_too_short_name_not_asked(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, dataclasses.replace(MARTIN, name="AB"))
    assert run(campaign_db, json_reply(200, page(result()))) == []
    assert "Entreprise à confirmer" in card(campaign_db, pid, NOW, PARIS).prospect.to_check


def test_C93_non_diffusible_nothing_stored(campaign_db: Engine) -> None:
    [pid] = add(campaign_db, MARTIN)
    run(campaign_db, json_reply(200, page(result(statut_diffusion="P"))))
    with campaign_db.connect() as conn:
        stored = conn.execute(
            select(prospects.c.company_json, prospects.c.registry_status)
            .where(prospects.c.id == pid)
        ).one()  # fmt: skip
    assert tuple(stored) == (None, "non diffusible")
