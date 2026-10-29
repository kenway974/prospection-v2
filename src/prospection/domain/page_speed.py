"""Vitesse du site sur mobile, mesurée par Google PageSpeed Insights (bloc « Le site »,
score d'opportunité, fiche « Pour l'appel »). Données mesurées, jamais devinées."""

from dataclasses import dataclass

SLOW_SCORE = 50  # en dessous : site lent sur mobile (barème de Google : rouge)
MAX_ISSUES = 3
# Audits Lighthouse les plus parlants pour un commerçant, dits simplement.
ISSUE_LABELS = {
    "uses-optimized-images": "Images trop lourdes",
    "modern-image-formats": "Images dans un format ancien",
    "uses-responsive-images": "Images plus grandes que l'écran du téléphone",
    "offscreen-images": "Images chargées avant d'être visibles",
    "render-blocking-resources": "Page bloquée par des fichiers à charger avant l'affichage",
    "unused-javascript": "Code JavaScript inutile",
    "unused-css-rules": "Styles CSS inutiles",
    "unminified-javascript": "Code JavaScript non compressé",
    "server-response-time": "Serveur lent à répondre",
    "uses-text-compression": "Textes envoyés sans compression",
    "uses-long-cache-ttl": "Fichiers rechargés à chaque visite",
    "total-byte-weight": "Page très lourde",
}


@dataclass(frozen=True)
class PageSpeed:
    score: int  # 0 à 100, performance mobile
    display_ms: int | None  # affichage du contenu principal (LCP)
    issues: tuple[str, ...]  # identifiants d'audits Lighthouse, du plus coûteux au moins


def is_slow(speed: PageSpeed | None) -> bool:
    return speed is not None and speed.score < SLOW_SCORE


def issue_labels(speed: PageSpeed) -> list[str]:
    return [ISSUE_LABELS[i] for i in speed.issues if i in ISSUE_LABELS][:MAX_ISSUES]


def speed_line(speed: PageSpeed) -> str:
    """« 34/100 · contenu affiché en 6,2 s » ; rien d'inventé si une mesure manque."""
    text = f"{speed.score}/100"
    if speed.display_ms is not None:
        seconds = f"{speed.display_ms / 1000:.1f}".replace(".", ",")
        text += f" · contenu affiché en {seconds} s"
    return text
