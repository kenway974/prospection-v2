"""Valeurs d'un prospect pour sa fiche Notion (C68, C71) : ce que l'app sait, rien d'inventé."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import Connection

from prospection.application.prospect_view import emails_of, insights
from prospection.domain.call_links import leader_name
from prospection.domain.crm_record import MAX_TEXT
from prospection.domain.site_guess import address_city
from prospection.storage.call_tracking import notes, open_action
from prospection.storage.crm_exports import campaign_name
from prospection.storage.mail_domains import mail_servers
from prospection.storage.prospect_list import ProspectRow

MAX_NOTES = MAX_TEXT


def _notes(conn: Connection, prospect_id: int) -> str | None:
    lines = [f"{n.created_at:%d/%m/%Y} : {n.text}" for n in notes(conn, prospect_id)]
    return "\n".join(lines)[:MAX_NOTES] or None


def _clip(values: dict[str, Any]) -> dict[str, Any]:
    """Textes coupés comme Notion les garde : la valeur relue reste comparable (C70)."""
    return {k: v[:MAX_TEXT] if isinstance(v, str) else v for k, v in values.items()}


def crm_values(conn: Connection, row: ProspectRow, now: datetime, today: str) -> dict[str, Any]:
    """Colonnes de l'app ; dates en texte ISO (jour du fuseau du propriétaire)."""
    day = date.fromisoformat(today)
    seen = insights(row, mail_servers(conn, [e.split("@")[-1] for e in emails_of(row)]), day)
    sure = row.company if row.company and row.registry_status == "sûr" else None
    action = open_action(conn, row.id)
    emails = emails_of(row)
    data = row.data
    return _clip({
        "Entreprise": data.get("name"), "ID app": data.get("place_id"),
        "Dirigeant": row.contact[0] or (leader_name(sure.leaders) if sure else None),
        "Mobile": row.contact[1], "Téléphone": data.get("phone"),
        "Email": emails[0] if emails else None,
        "Site": (row.site.url if row.site else None) or data.get("website"),
        "Fiche Google": data.get("maps_url"), "Métier": ", ".join(row.keywords) or None,
        "Ville": address_city(str(data.get("address") or "")) or data.get("address"),
        "SIREN": sure.siren if sure else None, "Score": seen.score, "Raison": seen.reason,
        "Notes app": _notes(conn, row.id),
        "Prochaine action": action.kind if action else None,
        "Date action": action.due_date.isoformat() if action else None,
        "Campagne": campaign_name(conn, row.id) or None, "Exporté le": today,
    })  # fmt: skip
