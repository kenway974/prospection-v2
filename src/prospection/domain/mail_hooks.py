"""Accroche personnalisée du mail d'audit : la première phrase. D'abord une phrase choc tirée
du premier point de l'audit (C171), sinon les faits connus sur l'entreprise (avis Google,
ancienneté, labels), selon le métier (C160). Règles dans `mail_rules.yaml`."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from prospection.domain.audit_mail_models import Condition
from prospection.domain.audit_mail_rules import load_mail_rules, sectors_for


@dataclass(frozen=True)
class LeadFacts:
    company: str
    rating: float | None
    reviews: int
    created: date | None
    labels: tuple[str, ...]
    has_site: bool
    today: date


def _years(facts: LeadFacts) -> int | None:
    if facts.created is None:
        return None
    return (
        facts.today.year
        - facts.created.year
        - ((facts.today.month, facts.today.day) < (facts.created.month, facts.created.day))
    )


def _months(facts: LeadFacts) -> int | None:
    if facts.created is None:
        return None
    return (facts.today.year - facts.created.year) * 12 + facts.today.month - facts.created.month


def _fits(c: Condition, f: LeadFacts, sectors: list[str]) -> bool:
    years, months = _years(f), _months(f)
    checks = [
        c.note_min is None or (f.rating is not None and f.rating >= c.note_min),
        c.avis_min is None or f.reviews >= c.avis_min,
        c.avec_site is None or c.avec_site == f.has_site,
        c.age_max_mois is None or (months is not None and 0 <= months <= c.age_max_mois),
        c.age_min_ans is None or (years is not None and years >= c.age_min_ans),
        c.label is None or c.label in f.labels,
        c.secteur is None or c.secteur in sectors,
    ]
    return all(checks)


def matching_hooks(
    facts: LeadFacts, keywords: Sequence[str], first_point: str | None = None
) -> list[tuple[str, str]]:
    """Accroches qui s'appliquent (modèle, texte rempli), la préférée d'abord. `first_point` :
    code du premier point du mail ; ses phrases choc passent seules quand il y en a (C171)."""
    rules = load_mail_rules()
    sectors = sectors_for(rules, keywords)
    values = {
        "entreprise": facts.company, "avis": str(facts.reviews), "ans": str(_years(facts) or ""),
        "note": f"{facts.rating:.1f}".replace(".", ",") if facts.rating is not None else "",
    }  # fmt: skip
    shock = rules.accroches_audit.get(first_point or "", [])
    if shock:
        upper = rules.accroche_majuscules
        return [(t, t.format_map(values).upper() if upper else t.format_map(values)) for t in shock]
    return [(h.texte, h.texte.format_map(values)) for h in rules.accroches
            if _fits(h.quand, facts, sectors)]  # fmt: skip
