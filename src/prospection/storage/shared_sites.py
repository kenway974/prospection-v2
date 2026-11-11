"""Sites partagés : combien d'autres entreprises ont le même nom de domaine (C174)."""

from sqlalchemy import ColumnElement, Connection, func, or_, select

from prospection.storage.schema_campaigns import prospects

_WEBSITE = prospects.c.data_json["website"].astext
_NAME: ColumnElement[str] = func.lower(func.trim(prospects.c.data_json["name"].astext))


def companies_on_host(conn: Connection, host: str, name: str) -> int:
    """Entreprises (noms différents de `name`) dont la fiche renvoie vers ce domaine, avec ou
    sans « www. », en http ou en https."""
    bare = host.lower().removeprefix("www.")
    hosts = [bare, f"www.{bare}"]
    patterns = [f"{scheme}://{h}{end}" for scheme in ("http", "https") for h in hosts
                for end in ("", "/%", ":%", "?%", "#%")]  # fmt: skip
    found = select(func.count(func.distinct(_NAME))).where(
        or_(*(_WEBSITE.ilike(p) for p in patterns)), _NAME.is_distinct_from(name.strip().lower())
    )
    return int(conn.execute(found).scalar_one())
