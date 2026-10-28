"""La tâche de fond vérifie le serveur mail des emails trouvés ou saisis (C53)."""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Engine

from prospection.storage.mail_domains import domains_to_check, save_mail_server

BATCH = 20


def check_mail_domains(
    engine: Engine, now: datetime, lookup: Callable[[str], str | None], batch: int = BATCH
) -> int:
    """Vérifie jusqu'à `batch` domaines pas encore vus (ou à revoir) ; renvoie leur nombre."""
    with engine.connect() as conn:
        domains = domains_to_check(conn, now, batch)
    for domain in domains:
        status = lookup(domain)
        with engine.begin() as conn:
            save_mail_server(conn, domain, status, now)
    return len(domains)
