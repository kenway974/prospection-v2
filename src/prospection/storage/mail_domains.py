"""Serveur mail des domaines d'emails, gardé par domaine (C53).

Revérifié après 30 jours ; un DNS muet est réessayé le lendemain.
"""

from datetime import datetime, timedelta

from sqlalchemy import Column, Connection, DateTime, Table, Text, select, text
from sqlalchemy.dialects.postgresql import insert

from prospection.storage.db import metadata

RECHECK_AFTER = timedelta(days=30)
RETRY_SILENT_AFTER = timedelta(days=1)

mail_domains = Table(
    "mail_domains", metadata,
    Column("domain", Text, primary_key=True), Column("status", Text),
    Column("checked_at", DateTime(timezone=True), nullable=False),
)  # fmt: skip

# Emails des prospects retenus : saisis sur la fiche, ou lus sur leur site
_EMAILS = """
    SELECT contact_email AS email FROM prospects WHERE contact_email IS NOT NULL
    UNION
    SELECT jsonb_array_elements_text(site_json -> 'contacts' -> 'emails') FROM prospects
    WHERE qualified AND jsonb_typeof(site_json -> 'contacts' -> 'emails') = 'array'
"""


def domains_to_check(conn: Connection, now: datetime, limit: int) -> list[str]:
    rows = conn.execute(
        text(f"""
            SELECT DISTINCT lower(split_part(e.email, '@', 2)) AS domain
            FROM ({_EMAILS}) e
            LEFT JOIN mail_domains m ON m.domain = lower(split_part(e.email, '@', 2))
            WHERE split_part(e.email, '@', 2) <> ''
              AND (m.domain IS NULL OR m.checked_at < :stale
                   OR (m.status IS NULL AND m.checked_at < :silent))
            ORDER BY domain LIMIT :limit
        """),  # noqa: S608 (texte fixe, valeurs en paramètres)
        {"stale": now - RECHECK_AFTER, "silent": now - RETRY_SILENT_AFTER, "limit": limit},
    )
    return [str(r.domain) for r in rows]


def save_mail_server(conn: Connection, domain: str, status: str | None, now: datetime) -> None:
    statement = insert(mail_domains).values(domain=domain, status=status, checked_at=now)
    conn.execute(statement.on_conflict_do_update(
        index_elements=["domain"], set_={"status": status, "checked_at": now}))  # fmt: skip


def mail_servers(conn: Connection, domains: list[str]) -> dict[str, str]:
    """Résultats connus (DNS muet exclu) pour ces domaines."""
    m = mail_domains.c
    rows = conn.execute(
        select(m.domain, m.status).where(m.domain.in_(domains), m.status.is_not(None))
    )
    return {str(r.domain): str(r.status) for r in rows}
