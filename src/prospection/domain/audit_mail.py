"""Mail d'audit : les points à citer et le texte proposé (C145).

Règles fixes (fichier `mail_rules.yaml`), sans IA : au plus 3 problèmes, les plus lourds pour
ce métier, chacun dit en trois temps (problème, effet sur le business, ce qu'il faut faire).
Le texte reste modifiable avant l'envoi ; la désinscription est ajoutée à l'envoi (C146).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from prospection.domain.audit_mail_rules import MailRules, load_mail_rules
from prospection.domain.trades import normalize

MAX_POINTS = 3


@dataclass(frozen=True)
class MailSender:
    name: str
    phone: str | None
    portfolio: str
    calendly: str | None


@dataclass(frozen=True)
class MailPoint:
    code: str
    title: str
    problem: str
    impact: str  # ce que ça coûte au business (adapté au métier)
    action: str


@dataclass(frozen=True)
class Draft:
    subject: str
    body: str


def _sectors(rules: MailRules, keywords: Sequence[str]) -> list[str]:
    words = " ".join(normalize(k) for k in keywords)
    return [
        name for name, sector in rules.secteurs.items()
        if any(re.search(rf"\b{re.escape(normalize(w))}", words) for w in sector.mots)
    ]  # fmt: skip


def choose_points(codes: Sequence[str], keywords: Sequence[str]) -> list[MailPoint]:
    """Problèmes de l'audit (codes) → au plus 3 points, du plus lourd au plus léger."""
    rules = load_mail_rules()
    sectors = [rules.secteurs[name] for name in _sectors(rules, keywords)]

    def weight(code: str) -> int:
        return rules.points[code].poids + sum(s.bonus.get(code, 0) for s in sectors)

    known = [c for c in dict.fromkeys(codes) if c in rules.points]
    chosen: list[MailPoint] = []
    groups: set[str] = set()
    for code in sorted(known, key=lambda c: -weight(c)):  # tri stable : ordre de l'audit
        point = rules.points[code]
        if point.groupe and point.groupe in groups:
            continue
        groups |= {point.groupe} if point.groupe else set()
        impact = next((s.impacts[code] for s in sectors if code in s.impacts), point.impact)
        chosen.append(MailPoint(code, point.titre, point.probleme, impact, point.action))
        if len(chosen) == MAX_POINTS:
            break
    return chosen


def draft_mail(points: Sequence[MailPoint], company: str, site: str, sender: MailSender) -> Draft:
    rules = load_mail_rules()
    count = f"{len(points)} point{'s' if len(points) > 1 else ''}"
    values = {"entreprise": company, "site": site, "expediteur": sender.name,
              "telephone": sender.phone or "", "portfolio": sender.portfolio,
              "calendly": sender.calendly or "", "nombre": count, "lien": ""}  # fmt: skip
    call = rules.appel_calendly if sender.calendly else rules.appel_sans_calendly
    signature = rules.signature
    if sender.phone:
        signature += "\n" + rules.signature_telephone
    blocks = [
        f"**{i}. {p.title}**\n- **{rules.constat} :** {p.problem}\n"
        f"- **{rules.cout} :** {p.impact}\n- **{rules.solution} :** {p.action}"
        for i, p in enumerate(points, 1)
    ]
    parts = [rules.intro, *blocks, rules.portfolio, call, signature]
    body = "\n\n".join(part.format_map(values) for part in parts)
    return Draft(rules.objet.format_map(values), body)
