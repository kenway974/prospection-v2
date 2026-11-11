"""C174 : un même nom de domaine chez plusieurs entreprises différentes."""

import dataclasses

from sqlalchemy import Engine

from prospection.domain.criteria import Verdict
from prospection.storage.campaigns import create_campaign
from prospection.storage.prospects import insert_prospect
from prospection.storage.shared_sites import companies_on_host
from tests.application.campaign_helpers import NOW, request
from tests.storage.test_campaigns import PLACE, STEPS


def _add(engine: Engine, name: str, website: str | None, place_id: str) -> None:
    place = dataclasses.replace(PLACE, name=name, website=website, place_id=place_id)
    with engine.begin() as conn:
        campaign_id = create_campaign(conn, request(), STEPS, NOW)
        insert_prospect(conn, campaign_id, place, "plombier", Verdict(True, (), ()), NOW, None)


def test_C174_counts_other_companies_on_the_same_host(mail_db: Engine) -> None:
    _add(mail_db, "Plomberie Martin", "https://www.reseau-pros.fr/martin", "a")
    _add(mail_db, "Durand Chauffage", "http://reseau-pros.fr/agence/durand", "b")
    _add(mail_db, "durand chauffage", "https://reseau-pros.fr/durand-2", "c")  # même entreprise
    _add(mail_db, "Leroy", "https://leroy.fr", "d")
    _add(mail_db, "Faux", "https://pas-reseau-pros.fr", "e")
    with mail_db.connect() as conn:
        assert companies_on_host(conn, "reseau-pros.fr", "Nouvelle SARL") == 2
        assert companies_on_host(conn, "www.reseau-pros.fr", "Plomberie Martin") == 1
        assert companies_on_host(conn, "leroy.fr", "Autre") == 1
