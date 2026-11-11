"""Application des migrations numérotées (au démarrage du conteneur)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text
from sqlalchemy.exc import ProgrammingError

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def run_migrations(database_url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")


def schema_ready(engine: Engine) -> bool:
    """Vrai si la base est à la dernière migration (la tâche de fond attend sinon : au
    déploiement, c'est le service web qui applique les migrations)."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    head = ScriptDirectory.from_config(config).get_current_head()
    try:
        with engine.connect() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except ProgrammingError:  # base vide : table des versions pas encore créée
        return False
    return current == head
