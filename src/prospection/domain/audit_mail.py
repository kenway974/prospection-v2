"""Mail d'audit : les points à citer et le texte proposé (C145).

Règles fixes (fichier `mail_rules.yaml`), sans IA : au plus 3 problèmes, les plus lourds pour
ce métier, chacun dit en trois temps (problème, effet sur le business, ce qu'il faut faire).
Le texte reste modifiable avant l'envoi ; la désinscription est ajoutée à l'envoi (C146).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from prospection.domain.audit_mail_rules import load_mail_rules, sectors_for

MAX_POINTS = 3
STRUCTURES = ("détaillée", "courte")  # constat, impact, solution ; ou une phrase par point


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


def choose_points(codes: Sequence[str], keywords: Sequence[str]) -> list[MailPoint]:
    """Problèmes de l'audit (codes) → au plus 3 points, du plus lourd au plus léger."""
    rules = load_mail_rules()
    sectors = [rules.secteurs[name] for name in sectors_for(rules, keywords)]

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


def draft_mail(
    points: Sequence[MailPoint], company: str, site: str, sender: MailSender,
    hook: str | None = None, subject: str | None = None, structure: str = STRUCTURES[0],
) -> Draft:  # fmt: skip
    """`site` vide : prospect sans site (C161) ; `hook` : accroche personnalisée (C160) ;
    `subject` (modèle d'objet) et `structure` : versions choisies (C162)."""
    rules = load_mail_rules()
    count = f"{len(points)} point{'s' if len(points) > 1 else ''}"
    values = {"entreprise": company, "site": site, "expediteur": sender.name,
              "telephone": sender.phone or "", "portfolio": sender.portfolio,
              "calendly": sender.calendly or "", "nombre": count, "lien": ""}  # fmt: skip
    call = rules.appel_telephone if sender.phone else rules.appel_sans_telephone  # C155
    if sender.calendly:
        call += "\n" + rules.calendly
    blocks = [
        f"**{i}. {p.title}**\n- **{rules.constat} :** {p.problem}\n"
        f"- **{rules.cout} :** {p.impact}\n- **{rules.solution} :** {p.action}"
        if structure == STRUCTURES[0]
        else f"**{i}. {p.title}**\n{p.impact} {p.action}"
        for i, p in enumerate(points, 1)
    ]
    intro = rules.intro if site else rules.intro_sans_site
    parts = [intro, *blocks, call, rules.portfolio, rules.signature]
    filled = [part.format_map(values) for part in parts]
    opening = [rules.salutation.format_map(values), *([hook] if hook else [])]  # déjà rempli
    body = "\n\n".join([*opening, *filled])
    return Draft((subject or rules.objets[0]).format_map(values), body)
