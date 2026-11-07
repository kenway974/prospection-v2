"""Mails d'audit envoyés et désinscriptions (C146, C148).

Seule l'empreinte de l'adresse est gardée ; une désinscription survit à la suppression du
prospect (droit d'opposition), l'envoi garde son jeton pour que le lien marche toujours.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Connection,
    DateTime,
    ForeignKey,
    Index,
    Table,
    Text,
    delete,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.db import metadata

TS = DateTime(timezone=True)
mail_sends = Table(
    "mail_sends", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("prospect_id", BigInteger, ForeignKey("prospects.id", ondelete="SET NULL")),
    Column("email_hash", Text, nullable=False), Column("token", Text, nullable=False, unique=True),
    Column("sent_at", TS, nullable=False), Column("bounced_at", TS),  # C157 : refusé
    Index("mail_sends_one_active", "prospect_id", unique=True,
          postgresql_where=text("bounced_at IS NULL")),
)  # fmt: skip
_ACTIVE = text("bounced_at IS NULL")
mail_optouts = Table(
    "mail_optouts", metadata,
    Column("email_hash", Text, primary_key=True), Column("created_at", TS, nullable=False),
)  # fmt: skip


def record_send(
    conn: Connection, prospect_id: int, email_hash: str, token: str, now: datetime
) -> bool:
    """Faux si un mail a déjà été envoyé à ce prospect (un seul envoi, même en double clic)."""
    statement = insert(mail_sends).values(prospect_id=prospect_id, email_hash=email_hash,
                                          token=token, sent_at=now)  # fmt: skip
    done = statement.on_conflict_do_nothing(index_elements=["prospect_id"], index_where=_ACTIVE)
    return conn.execute(done.returning(mail_sends.c.id)).scalar() is not None


def sent_at(conn: Connection, prospect_id: int) -> datetime | None:
    s = mail_sends.c
    active = s.prospect_id == prospect_id, s.bounced_at.is_(None)
    return conn.execute(select(s.sent_at).where(*active)).scalar()


def bounce(conn: Connection, prospect_id: int, now: datetime) -> str | None:
    """Marque l'envoi actif comme refusé ; rend l'empreinte de l'adresse, None sans envoi."""
    s = mail_sends.c
    done = conn.execute(
        update(mail_sends).where(s.prospect_id == prospect_id, s.bounced_at.is_(None))
        .values(bounced_at=now).returning(s.email_hash)
    )  # fmt: skip
    return done.scalar()


def opted_out(conn: Connection, hashes: list[str]) -> set[str]:
    o = mail_optouts.c
    return set(conn.execute(select(o.email_hash).where(o.email_hash.in_(hashes))).scalars())


def already_written(conn: Connection, hashes: list[str]) -> set[str]:
    """Adresses qui ont déjà reçu un mail d'audit (même pour un autre prospect)."""
    s = mail_sends.c
    return set(conn.execute(select(s.email_hash).where(s.email_hash.in_(hashes))).scalars())


def opt_out(conn: Connection, token: str, now: datetime) -> bool:
    """Bloque l'adresse de cet envoi ; faux si le jeton est inconnu."""
    s = mail_sends.c
    email_hash = conn.execute(select(s.email_hash).where(s.token == token)).scalar()
    if email_hash is None:
        return False
    conn.execute(insert(mail_optouts).values(email_hash=email_hash, created_at=now)
                 .on_conflict_do_nothing(index_elements=["email_hash"]))  # fmt: skip
    return True


def cancel_send(conn: Connection, token: str) -> None:
    """Envoi refusé par Gmail : la réservation est retirée, un nouvel essai reste possible."""
    conn.execute(delete(mail_sends).where(mail_sends.c.token == token))
