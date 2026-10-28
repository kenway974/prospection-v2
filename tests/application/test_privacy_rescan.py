"""C95 : une entreprise supprimée sur demande n'est plus jamais réenregistrée."""

from sqlalchemy import Engine

from prospection.application.campaign_step import run_step
from prospection.application.campaigns import create_campaign, progress
from prospection.application.privacy import erase_company
from tests.application.campaign_helpers import BOX, NOW, PRICING, api_place, pages, request
from tests.fake_http import fake_client


def _place_ids(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        return list(conn.exec_driver_sql("SELECT place_id FROM prospects ORDER BY id").scalars())


def test_C95_erased_company_not_stored_again_even_as_excluded(campaign_db: Engine) -> None:
    client, _ = fake_client(pages([api_place(1)], [api_place(1), api_place(2)]))
    first = create_campaign(campaign_db, request(target=1), NOW)
    run_step(campaign_db, BOX, client, PRICING, first, NOW)
    with campaign_db.connect() as conn:
        pid = conn.exec_driver_sql("SELECT id FROM prospects").scalar_one()
    erase_company(campaign_db, pid)
    second = create_campaign(campaign_db, request(target=5), NOW)
    for _ in range(5):
        if run_step(campaign_db, BOX, client, PRICING, second, NOW).done:
            break
    assert _place_ids(campaign_db) == ["place-2"]
    assert progress(campaign_db, second).found == 1
