"""C91 : la copie de la base se restaure (vrai pg_dump / pg_restore, base de test locale)."""

import uuid

from sqlalchemy import Engine, create_engine, make_url, text

from prospection.storage.backup_dump import dump_database, restore_database


def test_C91_restore_is_tested(engine: Engine, database_url: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO alerts (key, kind, message, link, created_at) "
                          "VALUES ('test-restauration', 'x', 'gardée', '/', now())"))  # fmt: skip
    copy = dump_database(database_url)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM alerts WHERE key = 'test-restauration'"))
    name = f"restauration_{uuid.uuid4().hex[:8]}"
    server = create_engine(database_url, isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    target = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    try:
        restore_database(target, copy)
        restored = create_engine(target)
        with restored.connect() as conn:
            kept = conn.execute(text("SELECT message FROM alerts WHERE key = 'test-restauration'"))
            assert kept.scalar_one() == "gardée"
        restored.dispose()
    finally:
        with server.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        server.dispose()


def test_C91_failed_restore_changes_nothing(engine: Engine, database_url: str) -> None:
    import pytest

    from prospection.storage.backup_dump import BackupFailed

    with engine.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM alembic_version")).scalar_one()
    with pytest.raises(BackupFailed):
        restore_database(database_url, b"pas une sauvegarde")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM alembic_version")).scalar_one() == before


def test_C91_copy_from_newer_client_restores_on_older_server() -> None:
    """pg_dump 17 écrit « SET transaction_timeout », inconnu de PostgreSQL 16 (Railway)."""
    from prospection.storage.backup_dump import for_older_servers

    script = b"SET statement_timeout = 0;\nSET transaction_timeout = 0;\nCREATE TABLE t ();\n"
    assert for_older_servers(script) == b"SET statement_timeout = 0;\nCREATE TABLE t ();\n"
