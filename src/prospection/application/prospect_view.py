"""Ce que la liste et la fiche disent d'un prospect : score, raison, drapeaux, confiance,
emails vérifiés (C53, C54, C57 à C60). Tout est recalculé à l'affichage depuis les données
gardées : une règle changée s'applique aussitôt à tous les prospects."""

from dataclasses import dataclass
from datetime import date

from prospection.domain.email_check import DOUBTFUL, INVALID, check_email, email_domain
from prospection.domain.opportunity import opportunity
from prospection.domain.qualification import confidence, reason
from prospection.domain.signals import Signals, signals_of
from prospection.storage.campaign_codec import decode_place
from prospection.storage.prospect_list import ProspectRow

SCORE = "score"  # tri de la liste : meilleures opportunités d'abord


@dataclass(frozen=True)
class Summary:
    score: int
    reason: str
    flagged: bool


@dataclass(frozen=True)
class Insights:
    score: int
    score_details: list[tuple[str, int]]
    reason: str
    confidence: list[tuple[str, str, str]]
    flags: list[str]
    emails: list[tuple[str, str, str]]  # adresse, statut, raison


def signals_for(row: ProspectRow, today: date) -> Signals:
    flags = tuple(row.to_check)
    return signals_of(decode_place(row.data), row.site, row.company, row.registry_status,
                      flags, today)  # fmt: skip


def summarize(row: ProspectRow, today: date) -> Summary:
    s = signals_for(row, today)
    return Summary(opportunity(s)[0], reason(s), bool(row.to_check))


def by_score(rows: list[ProspectRow], today: date) -> list[ProspectRow]:
    """Meilleures opportunités d'abord ; à score égal, l'ordre de la recherche."""
    return sorted(rows, key=lambda r: -summarize(r, today).score)


def emails_of(row: ProspectRow) -> list[str]:
    found = list(row.site.contacts.emails) if row.site and row.site.contacts else []
    return list(dict.fromkeys([*([row.contact[2]] if row.contact[2] else []), *found]))


def insights(row: ProspectRow, servers: dict[str, str], today: date) -> Insights:
    """`servers` : serveur mail connu de chaque domaine (vérifié par la tâche de fond)."""
    s = signals_for(row, today)
    score, details = opportunity(s)
    checks = [check_email(e, servers.get(email_domain(e) or "")) for e in emails_of(row)]
    emails = [(c.email, c.status, c.reason) for c in checks]
    doubts = [f"Email {c.email} : {c.reason}" for c in checks if c.status in (DOUBTFUL, INVALID)]
    return Insights(score, details, reason(s), confidence(s), [*row.to_check, *doubts], emails)
