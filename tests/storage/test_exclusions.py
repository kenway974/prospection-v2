"""C30 : ma liste de franchises ; C33 : ma liste noire."""

from sqlalchemy import Connection

from prospection.storage.exclusions import (
    load_exclusions,
    personal_lists,
    save_blacklist,
    save_personal_franchises,
)


def test_C30_C33_lists_saved_normalized(conn: Connection) -> None:
    save_personal_franchises(conn, ["Mon Enseigne", "", "mon enseigne"])
    save_blacklist(conn, ["Cuisines Lefèvre"])
    exclusions = load_exclusions(conn)
    assert exclusions.personal_franchises == frozenset({"mon enseigne"})
    assert exclusions.blacklist_names == frozenset({"cuisines lefevre"})
    assert personal_lists(conn) == (["Mon Enseigne"], ["Cuisines Lefèvre"])
