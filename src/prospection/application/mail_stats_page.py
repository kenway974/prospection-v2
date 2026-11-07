"""Page Stats des mails d'audit (C164) : ce qui mène à une conversation, d'après tes propres
envois. Conversation : réponse au mail (C163) ou appel où quelqu'un a répondu."""

from dataclasses import dataclass

from sqlalchemy import Engine

from prospection.domain.mail_stats import Row, SendResult, rank
from prospection.storage.mail_send_log import SentMail, all_sends

TALKED = frozenset({"intéressé", "à rappeler", "pas intéressé"})  # appel abouti
SECTIONS = (
    ("Objets", "objet"), ("Accroches", "accroche"), ("Structures", "structure"),
    ("Texte", "texte"), ("Points cités", "points"), ("Métiers", "métier"), ("Villes", "ville"),
    ("Site", "site"), ("Note Google", "note Google"), ("Avis Google", "avis Google"),
    ("Score", "score"), ("Ancienneté", "ancienneté"), ("Formulaire", "formulaire"),
)  # fmt: skip


@dataclass(frozen=True)
class StatsScreen:
    sends: int  # mails partis (refusés exclus)
    conversations: int
    replies: int
    bounced: int
    sections: list[tuple[str, list[Row]]]


def _result(sent: SentMail) -> SendResult:
    facts: dict[str, object] = {
        "objet": sent.subject_version, "accroche": sent.hook_version or "sans accroche",
        "structure": sent.structure,
        "texte": None if sent.edited is None else ("modifié" if sent.edited else "tel quel"),
        "points": list(sent.points), **sent.profile,
    }  # fmt: skip
    return SendResult(facts, sent.replied or sent.status in TALKED)


def stats_screen(engine: Engine) -> StatsScreen:
    with engine.connect() as conn:
        sends = all_sends(conn)
    delivered = [s for s in sends if not s.bounced]
    results = [_result(s) for s in delivered]
    return StatsScreen(
        len(delivered), sum(r.conversation for r in results), sum(s.replied for s in delivered),
        len(sends) - len(delivered), [(title, rank(results, key)) for title, key in SECTIONS],
    )  # fmt: skip
