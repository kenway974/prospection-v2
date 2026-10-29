"""Plusieurs prospects cochés dans la liste, supprimés en une fois (C129)."""

from collections.abc import Sequence

from sqlalchemy import Engine

from prospection.storage import privacy as store

MAX_SELECTION = 500  # au-delà, la page de confirmation deviendrait illisible


def selected(engine: Engine, prospect_ids: Sequence[int]) -> list[tuple[int, str]]:
    """Identifiant et nom des prospects cochés qui existent encore."""
    with engine.connect() as conn:
        return store.prospect_names(conn, prospect_ids[:MAX_SELECTION])


def delete_selection(engine: Engine, prospect_ids: Sequence[int], forever: bool) -> int:
    """`forever` : comme une suppression RGPD, l'entreprise ne sera plus jamais reprise."""
    ids = [i for i, _ in selected(engine, prospect_ids)]
    with engine.begin() as conn:
        if not forever:
            return store.delete_prospects(conn, ids)
        return sum(store.erase_company(conn, i) for i in ids)
