"""C80, C81 : tableau de bord et journal de chaque campagne."""

from sqlalchemy import Engine

from prospection.application.dashboard import dashboard, journal
from prospection.storage.campaigns import add_counts, add_event
from tests.application.campaign_helpers import NOW
from tests.application.test_call_tracking import add
from tests.storage.test_campaigns import PLACE


def test_C80_totals_rate_and_cost_per_qualified(campaign_db: Engine) -> None:
    add(campaign_db, PLACE)
    add(campaign_db)
    with campaign_db.begin() as conn:
        add_counts(conn, 1, NOW, found=40, excluded=30, qualified=10, cost_cents=350)
    board = dashboard(campaign_db)
    assert (board.campaigns, board.found, board.qualified) == (2, 40, 10)
    assert board.rate == 25 and board.cost_per_qualified == 35
    assert [line.rate for line in board.lines] == [None, 25]  # la plus récente d'abord


def test_C81_full_journal_with_errors(campaign_db: Engine) -> None:
    add(campaign_db, PLACE)
    with campaign_db.begin() as conn:
        for n in range(8):
            add_event(conn, 1, NOW, "info", f"page {n}")
        add_event(conn, 1, NOW, "warning", "Google trop sollicité : page ignorée")
    events = journal(campaign_db, 1)
    assert len(events) == 9 and events[0].level == "warning"
