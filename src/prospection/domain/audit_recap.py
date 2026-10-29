"""Résultat de l'audit du site en une ligne, pour la liste et la fiche (C136)."""

from prospection.domain.page_speed import is_slow
from prospection.domain.site_report import SiteReport

SHOWN = 3  # problèmes cités ; les autres sont comptés


def _short(problem: str) -> str:
    """Le constat sans son explication : « …, arrêté en 2023 : plus aucune statistique »."""
    text = problem.split(" : ")[0].strip()
    first = text.split(" ")[0]
    if first[1:].islower():  # « Pas de HTTPS » → « pas de HTTPS » ; « WordPress » reste tel quel
        return text[:1].lower() + text[1:]
    return text


def audit_recap(report: SiteReport | None) -> str | None:
    """None quand aucun audit n'a été fait (pas de site, page en construction, site
    injoignable) : la raison du prospect le dit déjà."""
    if report is None or report.parked or report.audit is None:
        return None
    problems = [_short(p) for p in report.audit.problems]
    parts = problems[:SHOWN] or ["aucun problème relevé"]
    extra = len(problems) - SHOWN
    if extra > 0:
        parts.append(f"+{extra} autre{'s' if extra > 1 else ''}")
    if report.speed and is_slow(report.speed):
        parts.append(f"lent sur mobile ({report.speed.score}/100)")
    return "Audit : " + " · ".join(parts)
