"""Code des problèmes des audits faits avant le 04/11/2026 (lecture seulement).

Ces audits ne gardaient que le texte : le début du texte donne le code. Un texte inconnu
donne un code vide (aucune règle du mail ne s'y applique).
"""

_PREFIXES = (
    ("Pas de HTTPS", "no_https"), ("Pas adapté au mobile", "no_mobile"),
    ("Pas de formulaire de contact", "no_form"), ("Caché de Google", "noindex"),
    ("Chargement lent", "slow"), ("Pas de titre de page", "no_title"),
    ("Ancien Google Analytics", "legacy_ga"), ("Aucun outil de suivi", "no_tracking"),
    ("Site pas mis à jour", "outdated"), ("Très peu de texte", "thin_content"),
    ("Pas de description pour Google", "no_description"),
    ("Pas de titre principal", "no_h1"), ("Aucun lien vers les réseaux", "no_social"),
    ("WordPress ancien", "old_wordpress"), ("Serveur PHP ancien", "old_php"),
    ("Fichiers chargés sans sécurité", "mixed_content"),
    ("Plusieurs titres principaux", "many_h1"), ("Images sans description", "missing_alts"),
)  # fmt: skip


def legacy_codes(problems: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        next((code for start, code in _PREFIXES if text.startswith(start)), "") for text in problems
    )
