"""Résultat du test d'une clé API (C03)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyCheck:
    ok: bool
    message: str


def no_answer(service_label: str) -> KeyCheck:
    return KeyCheck(False, f"{service_label} ne répond pas. Réessayez dans un instant.")


def unexpected(service_label: str) -> KeyCheck:
    return KeyCheck(False, f"Réponse inattendue de {service_label}. Réessayez plus tard.")
