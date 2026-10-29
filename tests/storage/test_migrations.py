"""C96, C127 : les migrations numérotées sont testées dans les deux sens."""

from alembic import command
from sqlalchemy import Engine, inspect, text

from tests.conftest import alembic_config


def test_C96_migrations_upgrade_then_downgrade_cleanly(engine: Engine, database_url: str) -> None:
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    assert "login_attempts" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "login_attempts" in inspect(engine).get_table_names()


def test_C127_existing_field_campaigns_recognised_by_their_name(
    engine: Engine, database_url: str
) -> None:
    config = alembic_config(database_url)
    command.downgrade(config, "0013")
    insert = text(
        "INSERT INTO campaigns (name, request_json, status, found, excluded, qualified,"
        " cost_cents, created_at, updated_at)"
        " VALUES (:name, '{}', 'done', 0, 0, 0, 0, now(), now())"
    )
    with engine.begin() as conn:
        for name in ("Terrain · Ma position · 28/10 10:00", "Cuisinistes Lyon"):
            conn.execute(insert, {"name": name})
    command.upgrade(config, "head")
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT name, kind FROM campaigns")).tuples().all()
        kinds: dict[str, str] = dict(rows)
        conn.execute(text("DELETE FROM campaigns"))
    assert kinds == {"Terrain · Ma position · 28/10 10:00": "terrain", "Cuisinistes Lyon": "appel"}
