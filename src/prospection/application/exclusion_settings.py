"""Réglages : ma liste de franchises (C30) et ma liste noire (C33)."""

from dataclasses import dataclass

from sqlalchemy import Engine

from prospection.storage.exclusions import personal_lists, save_blacklist, save_personal_franchises

MAX_NAMES = 500


class TooManyNames(ValueError):
    pass


@dataclass(frozen=True)
class ExclusionLists:
    franchises: list[str]
    blacklist: list[str]


def _lines(text: str) -> list[str]:
    names = [line for line in text.splitlines() if line.strip()]
    if len(names) > MAX_NAMES:
        raise TooManyNames(f"{MAX_NAMES} noms au plus par liste : retirez-en quelques-uns.")
    return names


def current_lists(engine: Engine) -> ExclusionLists:
    with engine.connect() as conn:
        return ExclusionLists(*personal_lists(conn))


def save_lists(engine: Engine, franchises: str, blacklist: str) -> None:
    """Remplace les deux listes ; liste trop longue : TooManyNames, rien ne change."""
    franchise_names, blacklist_names = _lines(franchises), _lines(blacklist)
    with engine.begin() as conn:
        save_personal_franchises(conn, franchise_names)
        save_blacklist(conn, blacklist_names)
