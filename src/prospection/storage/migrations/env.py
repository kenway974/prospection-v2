"""Environnement Alembic : applique les migrations sur l'URL configurée."""

from alembic import context
from sqlalchemy import create_engine

from prospection.storage.db import metadata

url = context.config.get_main_option("sqlalchemy.url")
if not url:
    from prospection.config import load_settings

    url = load_settings().database_url

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
