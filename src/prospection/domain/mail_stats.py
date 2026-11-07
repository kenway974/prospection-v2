"""Statistiques du mail d'audit (C162, C164) : version la moins utilisée d'abord ; classement
par taux de conversation (réponse au mail ou appel abouti), jamais sur les ouvertures."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

MIN_SENDS = 10  # en dessous, pas assez d'envois pour conclure


@dataclass(frozen=True)
class SendResult:
    facts: Mapping[str, object]  # versions utilisées, points cités, profil du lead
    conversation: bool


@dataclass(frozen=True)
class Row:
    label: str
    sends: int
    conversations: int

    @property
    def rate(self) -> int:
        return round(100 * self.conversations / self.sends) if self.sends else 0

    @property
    def enough(self) -> bool:
        return self.sends >= MIN_SENDS


def least_used(options: Sequence[str], counts: Mapping[str, int]) -> str:
    """La version la moins utilisée jusqu'ici ; à égalité, la première du fichier."""
    return min(options, key=lambda option: counts.get(option, 0))


def _values(value: object) -> list[str]:
    if isinstance(value, list | tuple):
        return [str(v) for v in value]
    return [] if value is None or value == "" else [str(value)]


def rank(results: Sequence[SendResult], key: str) -> list[Row]:
    """Une ligne par valeur de `key` : assez d'envois d'abord, puis meilleur taux."""
    sends: dict[str, int] = defaultdict(int)
    wins: dict[str, int] = defaultdict(int)
    for result in results:
        for label in _values(result.facts.get(key)):
            sends[label] += 1
            wins[label] += result.conversation
    rows = [Row(label, sends[label], wins[label]) for label in sends]
    return sorted(rows, key=lambda r: (not r.enough, -r.rate, -r.sends, r.label))
