"""C96 : les migrations numérotées sont testées dans les deux sens."""

from alembic import command
from sqlalchemy import Engine, inspect

from tests.conftest import alembic_config


def test_C96_migrations_upgrade_then_downgrade_cleanly(engine: Engine, database_url: str) -> None:
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    assert "login_attempts" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "login_attempts" in inspect(engine).get_table_names()
