"""Fiche Notion d'un prospect (base « Prospects v2 ») et règle « ne jamais écraser » (C68 à C71).

L'app n'écrit que ses colonnes, et seulement si la cellule est vide ou porte encore la valeur
que l'app y avait mise (C70). « Notes perso » jamais ; « Statut CRM » seulement à la création.
Aides de propriétés reprises de prospection-bot (services/crm/notion.py, version 530ba12).
"""

from datetime import date
from typing import Any

MAX_TEXT = 2000  # limite Notion par bloc de texte
TITLE, TEXT, PHONE, EMAIL, URL, NUMBER, DATE = "title", "text", "phone", "email", "url", "n", "d"
APP_COLUMNS = {
    "Entreprise": TITLE, "Dirigeant": TEXT, "Mobile": PHONE, "Téléphone": PHONE,
    "Email": EMAIL, "Site": URL, "Fiche Google": URL, "Métier": TEXT, "Ville": TEXT,
    "SIREN": TEXT, "Score": NUMBER, "Raison": TEXT, "Notes app": TEXT,
    "Prochaine action": TEXT, "Date action": DATE, "Campagne": TEXT, "Exporté le": DATE,
    "ID app": TEXT,
}  # fmt: skip
NEW_STATUS = "Nouveau"


def _text(value: str) -> list[dict[str, Any]]:
    return [{"text": {"content": value[:MAX_TEXT]}}]


def _property(kind: str, value: Any) -> dict[str, Any]:
    if kind == TITLE:
        return {"title": _text(str(value))}
    if kind == TEXT:
        return {"rich_text": _text(str(value))}
    if kind == PHONE:
        return {"phone_number": str(value)}
    if kind == EMAIL:
        return {"email": str(value)}
    if kind == URL:
        return {"url": str(value)[:MAX_TEXT]}
    if kind == NUMBER:
        return {"number": value}
    return {"date": {"start": value.isoformat() if isinstance(value, date) else str(value)}}


def to_properties(values: dict[str, Any], creating: bool) -> dict[str, Any]:
    props = {name: _property(APP_COLUMNS[name], v) for name, v in values.items() if v is not None}
    if creating:
        props["Statut CRM"] = {"status": {"name": NEW_STATUS}}
    return props


def merge(
    current: dict[str, Any] | None, written_before: dict[str, Any], wanted: dict[str, Any]
) -> dict[str, Any]:
    """Colonnes à écrire. `current` : la fiche telle qu'elle est dans Notion (None : à créer) ;
    `written_before` : ce que l'app y avait écrit la dernière fois."""
    if current is None:
        return {k: v for k, v in wanted.items() if v is not None}
    update = {}
    for name, value in wanted.items():
        now = current.get(name)
        untouched = now in (None, "") or now == written_before.get(name)
        if value is not None and untouched and now != value:
            update[name] = value
    return update
