"""Un seul envoyeur à la fois (verrou PostgreSQL), même si deux tâches de fond se
chevauchent pendant un déploiement : ni doublon, ni plafond ou rythme dépassé (C169, C177)."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, text

MAIL_LOCK, SMS_LOCK = 916_801, 916_802  # identifiants propres à l'app


@contextmanager
def single_sender(engine: Engine, key: int) -> Iterator[bool]:
    """Vrai si ce fil tient le verrou ; sinon un autre envoie déjà, ne rien faire."""
    with engine.connect() as conn:
        held = bool(conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar())
        try:
            yield held
        finally:
            if held:
                conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
