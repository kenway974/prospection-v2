"""C129 : supprimer plusieurs prospects d'un coup."""

from sqlalchemy import Connection, func, select

from prospection.storage.privacy import delete_prospects, erased_keys
from prospection.storage.prospect_list import prospect_ids
from prospection.storage.schema_campaigns import prospects
from tests.storage.test_call_tracking import prospects as add_prospects


def test_C129_selected_prospects_deleted_others_kept(conn: Connection) -> None:
    first, second, third = add_prospects(conn, "A", "B", "C")
    assert delete_prospects(conn, [first, third, 999_999]) == 2
    assert prospect_ids(conn, None, "", "trouves") == [second]
    assert conn.scalar(select(func.count()).select_from(prospects)) == 2  # l'exclu reste
    assert erased_keys(conn) == frozenset()  # simple suppression : une recherche peut les reprendre
