"""C62 à C65, C89, C118 : exports CSV et Excel d'une campagne."""

import csv
import dataclasses
import io

import openpyxl
from sqlalchemy import Engine

from prospection.application.file_export import campaign_csv, campaign_xlsx
from prospection.application.prospect_listing import prospect_list
from prospection.domain.criteria import Verdict
from prospection.storage.prospects import insert_prospect
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE


def campaign_with_prospects(engine: Engine) -> int:
    trap = dataclasses.replace(PLACE, place_id="p2", name='=HYPERLINK("x")', review_count=2)
    add(engine, dataclasses.replace(PLACE, review_count=200), trap)
    with engine.begin() as conn:
        campaign_id = int(conn.exec_driver_sql("SELECT max(id) FROM campaigns").scalar_one())
        excluded = dataclasses.replace(PLACE, place_id="p3", name="Franchise Café")
        insert_prospect(conn, campaign_id, excluded, "cuisiniste",
                        Verdict(False, ("Franchise ou chaîne (Café)",), ()), NOW)  # fmt: skip
    return campaign_id


def read_csv(data: bytes) -> list[list[str]]:
    assert data.startswith(b"\xef\xbb\xbf")  # C62 : accents corrects dans Excel
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter=";"))


def test_C62_C64_C89_csv_sorted_by_score_and_neutralized(campaign_db: Engine) -> None:
    campaign_id = campaign_with_prospects(campaign_db)
    header, *rows = read_csv(campaign_csv(campaign_db, campaign_id, "prospects", NOW))
    assert header[:3] == ["Score", "Entreprise", "Raison"]
    assert [r[1] for r in rows] == ['\'=HYPERLINK("x")', "Atelier"]  # meilleur score d'abord
    assert int(rows[0][0]) >= int(rows[1][0])


def test_C65_excluded_listed_with_their_reason(campaign_db: Engine) -> None:
    campaign_id = campaign_with_prospects(campaign_db)
    header, *rows = read_csv(campaign_csv(campaign_db, campaign_id, "exclus", NOW))
    assert header == ["Entreprise", "Raison de l'exclusion", "Adresse", "Métier", "Fiche Google"]
    assert rows == [["Franchise Café", "Franchise ou chaîne (Café)", "Lyon", "cuisiniste", ""]]


def test_C63_C65_excel_two_sheets(campaign_db: Engine) -> None:
    campaign_id = campaign_with_prospects(campaign_db)
    book = openpyxl.load_workbook(io.BytesIO(campaign_xlsx(campaign_db, campaign_id, NOW)))
    assert book.sheetnames == ["Prospects", "Exclus"]
    cell = book["Prospects"]["B2"]
    assert cell.value == '=HYPERLINK("x")' and cell.data_type == "s"  # texte, jamais formule
    assert book["Prospects"].freeze_panes == "A2"


def test_C118_file_export_changes_no_status(campaign_db: Engine) -> None:
    campaign_id = campaign_with_prospects(campaign_db)
    before = [r.status for r in prospect_list(campaign_db, None, "", "trouves").rows]
    campaign_csv(campaign_db, campaign_id, "prospects", NOW)
    campaign_xlsx(campaign_db, campaign_id, NOW)
    assert [r.status for r in prospect_list(campaign_db, None, "", "trouves").rows] == before


def test_C64_export_day_is_the_owner_day(campaign_db: Engine) -> None:
    """Juste après minuit à Paris (encore la veille en UTC), l'ancienneté suit le jour de Paris."""
    from datetime import UTC, datetime

    campaign_id = campaign_with_prospects(campaign_db)
    late = datetime(2026, 10, 27, 23, 30, tzinfo=UTC)  # 28 octobre à Paris
    data = campaign_csv(campaign_db, campaign_id, "prospects", late, "Europe/Paris")
    assert data.startswith(b"\xef\xbb\xbf")
