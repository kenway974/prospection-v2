"""C148 : une adresse désinscrite ne part plus ni dans les exports ni dans Notion."""

import dataclasses
from datetime import UTC, datetime

from sqlalchemy import Engine

from prospection.application.crm_values import crm_values
from prospection.application.file_export import campaign_csv
from prospection.domain.mail_message import email_fingerprint
from prospection.storage.prospect_list import load_prospect
from tests.application.campaign_helpers import BOX, NOW
from tests.application.mail_helpers import CONTACTS, SITE, add_audited
from tests.application.test_file_export import read_csv

BLOCKED = "contact@martin.fr"


def opt_out(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO mail_optouts VALUES (%(h)s, %(at)s)",
            {"h": email_fingerprint(BLOCKED, BOX.pepper), "at": datetime(2026, 10, 1, tzinfo=UTC)},
        )


def test_C148_opted_out_address_left_out_of_exports_and_crm(mail_db: Engine) -> None:
    only = dataclasses.replace(SITE, contacts=dataclasses.replace(CONTACTS, emails=(BLOCKED,)))
    pid = add_audited(mail_db, only)
    with mail_db.connect() as conn:
        campaign_id = int(conn.exec_driver_sql("SELECT max(id) FROM campaigns").scalar_one())
    header, row = read_csv(campaign_csv(mail_db, campaign_id, "prospects", NOW, pepper=BOX.pepper))
    assert row[header.index("Email")] == BLOCKED  # pas encore désinscrit
    opt_out(mail_db)
    header, row = read_csv(campaign_csv(mail_db, campaign_id, "prospects", NOW, pepper=BOX.pepper))
    assert row[header.index("Email")] == ""
    with mail_db.connect() as conn:
        prospect = load_prospect(conn, pid)
        assert prospect is not None
        assert crm_values(conn, prospect, NOW, "2026-10-25", BOX.pepper)["Email"] is None
