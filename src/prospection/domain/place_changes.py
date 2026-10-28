"""Ce qui a changé sur la fiche Google d'un établissement (C76), en mots simples."""

import re

from prospection.domain.place import Place

CLOSED = {
    "CLOSED_PERMANENTLY": "Fermé définitivement",
    "CLOSED_TEMPORARILY": "Fermé temporairement",
}


def _field(label: str, old: str | None, new: str | None) -> list[str]:
    if old == new:
        return []
    if not old:
        return [f"{label} ajouté"]
    return [f"{label} supprimé"] if not new else [f"{label} changé"]


def place_changes(old: Place, new: Place) -> list[str]:
    changes = []
    if new.business_status != old.business_status:
        if new.business_status in CLOSED:
            changes.append(CLOSED[new.business_status])
        elif old.business_status in CLOSED and new.business_status == "OPERATIONAL":
            changes.append("Rouvert")
    if new.name != old.name:
        changes.append("Nom changé")
    phones = [re.sub(r"\D", "", p) if p else None for p in (old.phone, new.phone)]
    return changes + _field("Site", old.website, new.website) + _field("Téléphone", *phones)
