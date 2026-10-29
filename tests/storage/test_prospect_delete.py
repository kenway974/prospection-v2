"""C129 : supprimer plusieurs prospects d'un coup."""

from sqlalchemy import Connection, func, select

from prospection.storage.privacy import delete_prospects, erased_keys
from prospection.storage.prospect_list import load_session, prospect_ids, start_session
from prospection.storage.schema_campaigns import prospects
from tests.storage.test_call_tracking import prospects as add_prospects
from tests.storage.test_campaigns import NOW


def test_C129_selected_prospects_deleted_others_kept(conn: Connection) -> None:
    first, second, third = add_prospects(conn, "A", "B", "C")
    assert delete_prospects(conn, [first, third, 999_999]) == 2
    assert prospect_ids(conn, None, "", "trouves") == [second]
    assert conn.scalar(select(func.count()).select_from(prospects)) == 2  # l'exclu reste
    assert erased_keys(conn) == frozenset()  # simple suppression : une recherche peut les reprendre


def test_C129_deleted_prospects_leave_the_call_session(conn: Connection) -> None:
    first, second, third = add_prospects(conn, "A", "B", "C")
    start_session(conn, [first, second, third], NOW)
    delete_prospects(conn, [second])
    session = load_session(conn)
    assert session is not None and session.queue == [first, third]
