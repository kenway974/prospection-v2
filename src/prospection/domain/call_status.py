"""Statuts d'un prospect et action proposée après un appel (C102, C103)."""

from datetime import date, timedelta

TO_CALL = "à appeler"
INTERESTED = "intéressé"
EXPORTED = "exporté"  # posé seulement par un export réussi (lot 7)
CALL_RESULTS = (
    "intéressé", "à rappeler", "pas intéressé", "messagerie", "pas joint", "faux numéro",
)  # fmt: skip
STATUSES = (TO_CALL, *CALL_RESULTS, EXPORTED)
ACTION_KINDS = {
    "rappeler": "Rappeler", "devis": "Envoyer un devis", "rendez-vous": "Rendez-vous",
    "passer": "Passer",
}  # fmt: skip


class InvalidStatus(ValueError):
    pass


def check_result(status: str) -> str:
    """Résultat d'appel choisi à l'écran ; tout autre texte est refusé."""
    if status not in CALL_RESULTS:
        raise InvalidStatus(status)
    return status


def proposed_action(status: str, today: date) -> tuple[str, date] | None:
    """« À rappeler » ou « messagerie » proposent : Rappeler demain."""
    return (
        ("rappeler", today + timedelta(days=1)) if status in ("à rappeler", "messagerie") else None
    )
