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


def test_worker_never_waits_forever_for_a_newer_database(engine: Engine) -> None:
    """Le web, déjà redéployé, a appliqué une migration que ce worker ne connaît pas."""
    with engine.begin() as conn:
        current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        conn.execute(text("UPDATE alembic_version SET version_num = '9999'"))
    try:
        assert schema_ready(engine)
    finally:
        with engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": current})
