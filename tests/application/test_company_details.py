"""C149, C150 : la tâche de fond complète chaque entreprise (registre gratuit, puis INPI)."""

import dataclasses
from collections.abc import Callable

import httpx
from sqlalchemy import Engine

from prospection.application.api_keys import key_statuses, store_key
from prospection.application.company_details import detail_companies
from prospection.domain.services import Service
from prospection.storage.prospect_list import load_prospect
from prospection.storage.registry_status import SURE, save_match
from tests.application.campaign_helpers import BOX, NOW
from tests.application.test_call_tracking import add
from tests.domain.test_company import LYON_SAS
from tests.fake_http import fake_client
from tests.sources.test_company_details import DETAILS
from tests.sources.test_company_registry import page, result
from tests.sources.test_rne import company as rne_answer
from tests.storage.test_campaigns import PLACE

SIRENE = dataclasses.replace(LYON_SAS, siren="912345678", leaders=(), finances=None)


def handler(rne_status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.host == "recherche-entreprises.api.gouv.fr":
            return httpx.Response(200, json=page(result(**DETAILS)))
        if request.url.path.endswith("/sso/login"):
            return httpx.Response(200, json={"token": "jeton"})
        return httpx.Response(rne_status, json=rne_answer())

    return answer


def known(engine: Engine) -> int:
    [pid] = add(engine, PLACE)
    with engine.begin() as conn:
        save_match(conn, pid, SIRENE, SURE)
    return pid


def run(engine: Engine, rne_status: int = 200) -> list[httpx.Request]:
    client, recorder = fake_client(handler(rne_status))
    detail_companies(engine, BOX, client, NOW, pause=0)
    return recorder.requests


def company_of(engine: Engine, pid: int):  # type: ignore[no-untyped-def]
    with engine.connect() as conn:
        row = load_prospect(conn, pid)
    assert row is not None and row.company is not None
    return row.company


def test_C149_registry_details_added_once(campaign_db: Engine) -> None:
    pid = known(campaign_db)
    assert len(run(campaign_db)) == 1  # pas de clé INPI : registre gratuit seulement
    company = company_of(campaign_db, pid)
    assert company.labels == ("est_rge", "est_patrimoine_vivant") and company.leaders
    assert company.open_sites == 3 and company.purpose is None
    assert run(campaign_db) == []


def test_C150_rne_details_added_when_inpi_key_is_set(campaign_db: Engine) -> None:
    pid = known(campaign_db)
    run(campaign_db)
    store_key(campaign_db, BOX, Service.INPI, "k@gmail.com:secret", NOW)
    requests = run(campaign_db)
    assert [r.url.path for r in requests] == ["/api/sso/login", "/api/companies/912345678"]
    company = company_of(campaign_db, pid)
    assert company.purpose == "La conception et la pose de cuisines."
    assert company.domains == ("cuisines-martin.fr",) and company.labels  # rien de perdu
    assert run(campaign_db) == []


def test_C150_inpi_down_is_retried_later(campaign_db: Engine) -> None:
    pid = known(campaign_db)
    store_key(campaign_db, BOX, Service.INPI, "k@gmail.com:secret", NOW)
    run(campaign_db, rne_status=503)
    assert company_of(campaign_db, pid).purpose is None
    run(campaign_db)
    assert company_of(campaign_db, pid).purpose is not None


def test_C150_refused_inpi_credentials_are_not_retried(campaign_db: Engine) -> None:
    known(campaign_db)
    store_key(campaign_db, BOX, Service.INPI, "k@gmail.com:faux", NOW)

    def refuse(request: httpx.Request) -> httpx.Response:
        if request.url.host == "recherche-entreprises.api.gouv.fr":
            return httpx.Response(200, json=page(result(**DETAILS)))
        return httpx.Response(401, json={})

    client, recorder = fake_client(refuse)
    detail_companies(campaign_db, BOX, client, NOW, pause=0)
    detail_companies(campaign_db, BOX, client, NOW, pause=0)
    assert [r.url.path for r in recorder.requests].count("/api/sso/login") == 1
    status = next(s for s in key_statuses(campaign_db, BOX) if s.service is Service.INPI)
    assert status.test_ok is False and "data.inpi.fr" in (status.test_message or "")
