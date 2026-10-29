"""Résultat de l'audit du site en une ligne, pour la liste et la fiche (C136)."""

from prospection.domain.page_speed import is_slow
from prospection.domain.site_report import SiteReport

SHOWN = 3  # problèmes cités ; les autres sont comptés


def _short(problem: str) -> str:
    """Le constat sans son explication : « …, arrêté en 2023 : plus aucune statistique »."""
    text = problem.split(" : ")[0].strip()
    return text[:1].lower() + text[1:]


def audit_recap(report: SiteReport | None) -> str | None:
    """None quand il n'y a rien à auditer (pas de site, page en construction, pas lu) :
    la raison du prospect le dit déjà."""
    if report is None or report.parked:
        return None
    if report.audit is None:
        return f"Audit : {_short(report.problem)}" if report.problem else None
    problems = [_short(p) for p in report.audit.problems]
    parts = problems[:SHOWN] or ["aucun problème relevé"]
    extra = len(problems) - SHOWN
    if extra > 0:
        parts.append(f"+{extra} autre{'s' if extra > 1 else ''}")
    if report.speed and is_slow(report.speed):
        parts.append(f"lent sur mobile ({report.speed.score}/100)")
    return "Audit : " + " · ".join(parts)
