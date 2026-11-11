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
    """Faux seulement si la base est en retard sur ce code (la tâche de fond attend : au
    déploiement, c'est le service web qui applique les migrations). Une base plus récente que
    ce code (web redéployé avant) n'est jamais une raison d'attendre sans fin."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(config)
    try:
        with engine.connect() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except ProgrammingError:  # base vide : table des versions pas encore créée
        return False
    known = {r.revision for r in script.walk_revisions()}
    return current not in known or current in script.get_heads()
