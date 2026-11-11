"""La tâche de fond attend que la base soit à jour avant de travailler (déploiement :
le service web applique les migrations, la tâche de fond peut démarrer avant)."""

from sqlalchemy import Engine, text

from prospection.storage.migrate import schema_ready


def test_worker_waits_until_migrations_are_applied(engine: Engine) -> None:
    assert schema_ready(engine)
    with engine.begin() as conn:
        current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        conn.execute(text("UPDATE alembic_version SET version_num = '0018'"))
    try:
        assert not schema_ready(engine)
    finally:
        with engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": current})
